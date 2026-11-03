"""Run a Revizor x86 program against a fresh WRUH model and native execution."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path
from types import SimpleNamespace

from corpus.native.sandbox import command
from extractor.corpus_probe import native_model
from extractor.corpus_runner import CorpusRunner, STORAGE
from extractor.revizor_partitions import solve_samples

STORAGE_SIZE = 16384
HARNESS = r'''
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
extern unsigned long division(unsigned long, unsigned long, unsigned char *);
int main(int argc, char **argv) {
  if (argc != 6) return 64;
  uint32_t x = (uint32_t)strtoul(argv[4], 0, 10);
  uint32_t y = (uint32_t)strtoul(argv[5], 0, 10);
  static unsigned char storage[16384] __attribute__((aligned(16)));
  for (unsigned i = 0; i < 8; ++i) {
    uint32_t word = y ^ i;
    for (unsigned j = 0; j < 4; ++j) storage[4*i+j] = word >> (8*j);
  }
  unsigned long result = division(x, y, storage);
  printf("%lu", result);
  for (unsigned i = 0; i < sizeof storage; ++i) printf(" %02x", storage[i]);
  puts("");
  return 0;
}
'''


def wrap_assembly(source: str) -> str:
    """Give the generated case an ABI entry and the scratch base it expects."""
    source = source.replace(".section .data.main", ".section .text")
    entry = ".function_0:"
    exit_label = ".test_case_exit:nop"
    if source.count(entry) != 1 or source.count(exit_label) != 1:
        raise ValueError("unexpected Revizor entry/exit layout")
    prologue = (".globl division\n.type division,@function\ndivision:\n"
                "push rbp\npush rbx\npush r12\npush r13\npush r14\npush r15\n"
                "mov r14, rdx\nxor eax, eax\nxor ebx, ebx\nxor ecx, ecx\n"
                "xor edx, edx\nxor ebp, ebp\nxor r8d, r8d\nxor r9d, r9d\n"
                "xor r10d, r10d\nxor r11d, r11d\nxor r12d, r12d\n"
                "xor r13d, r13d\nxor r15d, r15d\n")
    epilogue = (".test_case_exit:nop\npop r15\npop r14\npop r13\npop r12\n"
                "pop rbx\npop rbp\nret\n.size division,.-division\n"
                ".section .note.GNU-stack,\"\",@progbits\n")
    return source.replace(entry, prologue + entry).replace(exit_label, epilogue)


def compare(source: str, object_path: Path, sample_count: int,
            progress_path: Path | None = None, *, solver_timeout_ms: int = 30000,
            seed: int = 1, path_indices: set[int] | None = None,
            solver_statistics: bool = False) -> dict:
    from elftools.elf.elffile import ELFFile
    import angr

    with object_path.open("rb") as source_object:
        section = ELFFile(source_object).get_section_by_name(".data.main")
        if section is None:
            raise ValueError("Revizor object has no main code section")
        original = section.data()
    with tempfile.TemporaryDirectory(prefix="wruh-revizor-") as tmp:
        directory = Path(tmp)
        (directory / "case.S").write_text(wrap_assembly(source))
        (directory / "harness.c").write_text(HARNESS)
        candidate = directory / "candidate"
        subprocess.run([os.environ.get("WRUH_NATIVE_CC", "clang"), "-fno-integrated-as", "-O0", "-no-pie",
                        str(directory / "harness.c"), str(directory / "case.S"),
                        "-o", str(candidate)], check=True)
        raw = candidate.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        project = angr.Project(str(candidate), auto_load_libs=False)
        function = project.loader.find_symbol("division")
        if function is None or original not in project.loader.memory.load(function.rebased_addr, function.size):
            raise ValueError("linked case differs from Revizor's assembled program")
        evidence = {"sha256": digest, "elf_base64": base64.b64encode(raw).decode()}
        if progress_path is not None:
            progress_path.with_suffix(".case.json").write_text(json.dumps(evidence) + "\n")
        scan = directory / "scan.json"
        scan.write_text(json.dumps({"optimization": "0", "elf_sha256": digest,
                                    "elf_base64": evidence["elf_base64"]}))
        model = native_model(SimpleNamespace(scan=str(scan), root="division"))
        if model["status"] != "PASS" or model["elf_sha256"] != digest:
            return {"status": "EXTRACTION_INCOMPLETE", **evidence, "model": model}
        candidate.chmod(0o500)
        if hashlib.sha256(candidate.read_bytes()).hexdigest() != digest:
            raise RuntimeError("candidate changed after extraction")
        runner = CorpusRunner(model["fresh_model"])
        try:
            samples, paths = solve_samples(model, sample_count, timeout_ms=solver_timeout_ms,
                                           seed=seed, path_indices=path_indices,
                                           statistics=solver_statistics)
        except Exception as error:
            return {"status": "PARTITION_INCOMPLETE", **evidence,
                    "error_type": type(error).__name__, "error": str(error)}
        partition_summary = {"method": "composed_path_guards_smt", "paths": paths,
                             "sample_count": len(samples), "requested_samples": sample_count}
        if progress_path is not None:
            progress_path.with_suffix(".partitions.json").write_text(
                json.dumps(partition_summary, indent=2) + "\n")
            progress_path.with_suffix(".inputs.json").write_text(
                json.dumps(samples, separators=(",", ":")) + "\n")
        results = []
        def record(item: dict) -> None:
            results.append(item)
            if progress_path is not None:
                with progress_path.open("a") as stream:
                    stream.write(json.dumps(item, separators=(",", ":")) + "\n")
            if len(results) % 100 == 0:
                print(f"native comparisons: {len(results)}/{sample_count}", flush=True)

        for sample in samples:
            x, y = sample["x"], sample["y"]
            path_id = sample["path_id"]
            try:
                simulated = runner.run((2, 0, 0, x, y), limit=1024,
                                       storage_size=STORAGE_SIZE, extra_registers={"rdx": STORAGE})
            except Exception as error:
                record({"status": "MODEL_INCOMPLETE", "x": x, "y": y, "path_id": path_id,
                        "error_type": type(error).__name__, "error": str(error)})
                continue
            try:
                native = subprocess.run(command(candidate, (2, 0, 0, x, y)), text=True,
                                        capture_output=True, timeout=5)
            except subprocess.TimeoutExpired:
                record({"status": "NATIVE_INCOMPLETE", "x": x, "y": y, "path_id": path_id, "error": "timeout"})
                continue
            if native.returncode:
                record({"status": "NATIVE_INCOMPLETE", "x": x, "y": y, "path_id": path_id,
                        "stderr": native.stderr, "exit": native.returncode})
                continue
            fields = native.stdout.split()
            if len(fields) != STORAGE_SIZE + 1:
                record({"status": "NATIVE_INCOMPLETE", "x": x, "y": y, "path_id": path_id, "stdout": native.stdout})
                continue
            observed = (int(fields[0]), [int(item, 16) for item in fields[1:]])
            expected = (simulated.get("result"), simulated.get("memory"))
            status = ("MODEL_INCOMPLETE" if simulated["status"] != "RETURN" else
                      "MATCH" if observed == expected else "MISMATCH")
            if status == "MATCH":
                trace = json.dumps(simulated["trace"], sort_keys=True, separators=(",", ":")).encode()
                record({"status": status, "x": x, "y": y, "path_id": path_id,
                        "model_path_sha256": hashlib.sha256(trace).hexdigest()})
            else:
                record({"status": status, "x": x, "y": y, "path_id": path_id,
                        "model": simulated, "native": observed})
        status = ("MATCH" if len(results) == sample_count and all(item["status"] == "MATCH" for item in results)
                  else "INCOMPLETE_OR_MISMATCH")
        return {"status": status, **evidence, "partition_summary": partition_summary, "samples": results}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("assembly")
    parser.add_argument("--output", required=True)
    parser.add_argument("--samples", type=int, default=1000)
    parser.add_argument("--solver-timeout-ms", type=int, default=30000)
    parser.add_argument("--path-index", type=int, action="append")
    parser.add_argument("--solver-statistics", action="store_true")
    parser.add_argument("--seed", type=int, default=1)
    args = parser.parse_args()
    if args.samples < 1 or args.solver_timeout_ms < 1:
        parser.error("sample count and solver timeout must be positive")
    if Path(args.output).exists() or Path(args.output + ".progress.jsonl").exists():
        parser.error("output or progress file already exists")
    assembly = Path(args.assembly)
    result = compare(assembly.read_text(), assembly.with_suffix(".o"), args.samples,
                     Path(args.output + ".progress.jsonl"),
                     solver_timeout_ms=args.solver_timeout_ms, seed=args.seed,
                     path_indices=set(args.path_index) if args.path_index is not None else None,
                     solver_statistics=args.solver_statistics)
    Path(args.output).write_text(json.dumps(result, indent=2) + "\n")
    print(result["status"])
    if result["status"] != "MATCH":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
