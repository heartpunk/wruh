"""Native differential and two identity properties for composed Revizor functions."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import secrets
import subprocess
import tempfile
from pathlib import Path

import angr
from ayxg.eval import eval_expr, eval_update
from ayxg.qfabv import BoolSort, QFAbvExpr, QFAbvUpdate, decode_sort
from elftools.elf.elffile import ELFFile

from corpus.native.sandbox import command
from extractor.binary_cfg import build_static_cfg
from extractor.binary_inventory import PinnedBinary, exact_symbol_inventory_policy, inventory_project
from extractor.corpus_runner import CorpusRunner, RETURN, STORAGE
from extractor.fresh import extract_fresh_function
from extractor.fresh_composition import compose_fresh_paths
from extractor.revizor_differential import HARNESS, STORAGE_SIZE, wrap_assembly
from extractor.revizor_partitions import solve_samples


WRAPPERS = {
    "plain": "return f(x, y, storage);",
    "left_identity": "return f(identity(x, y, storage), y, storage);",
    "right_identity": "return identity(f(x, y, storage), y, storage);",
    "two_functions": "return g(f(x, y, storage), y, storage);",
}


def _named_assembly(source: str, name: str) -> str:
    wrapped = wrap_assembly(source)
    for old, new in ((".globl division", f".globl {name}"),
                     (".type division,@function", f".type {name},@function"),
                     ("division:\n", f"{name}:\n"),
                     (".size division,.-division", f".size {name},.-{name}")):
        if wrapped.count(old) != 1:
            raise ValueError(f"unexpected generated wrapper: {old}")
        wrapped = wrapped.replace(old, new)
    return wrapped


def _original_code(case: Path) -> bytes:
    with case.with_suffix(".o").open("rb") as stream:
        section = ELFFile(stream).get_section_by_name(".data.main")
        if section is None:
            raise ValueError(f"Revizor object has no main code section: {case}")
        return section.data()


def _compile_and_extract(directory: Path, mode: str, first: Path, second: Path) -> dict:
    directory.mkdir()
    print(f"{mode}: compile", flush=True)
    names = ("f", "g") if mode == "two_functions" else ("f",)
    sources = (first, second) if mode == "two_functions" else (first,)
    for name, source in zip(names, sources, strict=True):
        (directory / f"{name}.S").write_text(_named_assembly(source.read_text(), name))
    wrapper = ("\nextern unsigned long f(unsigned long, unsigned long, unsigned char *);\n"
               "extern unsigned long g(unsigned long, unsigned long, unsigned char *);\n"
               "__attribute__((noinline)) unsigned long identity(unsigned long x, "
               "unsigned long y, unsigned char *storage) { (void)y; (void)storage; return x; }\n"
               "__attribute__((noinline)) unsigned long division(unsigned long x, "
               "unsigned long y, unsigned char *storage) { " + WRAPPERS[mode] + " }\n")
    (directory / "harness.c").write_text(HARNESS + wrapper)
    binary = directory / "candidate"
    subprocess.run([os.environ.get("WRUH_NATIVE_CC", "clang"), "-fno-integrated-as",
                    "-fno-inline", "-fno-stack-protector", "-O0", "-no-pie",
                    str(directory / "harness.c"), *(str(directory / f"{name}.S") for name in names),
                    "-o", str(binary)], check=True)
    raw = binary.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    project = angr.Project(str(binary), auto_load_libs=False)
    for name, source in zip(names, sources, strict=True):
        symbol = project.loader.find_symbol(name)
        if symbol is None or _original_code(source) not in project.loader.memory.load(symbol.rebased_addr, symbol.size):
            raise ValueError(f"linked {name} differs from Revizor object {source}")
    roots = ("division", *names, "identity") if "identity" in mode else ("division", *names)
    manifest = inventory_project(project, binary, exact_symbol_inventory_policy(roots))
    pinned = PinnedBinary(binary, manifest, project)
    cfg = build_static_cfg(pinned)
    functions = []
    for root in roots:
        print(f"{mode}: extract {root}", flush=True)
        functions.append(extract_fresh_function(pinned, cfg, root))
    functions = tuple(functions)
    runner = CorpusRunner(functions[0].to_data())
    print(f"{mode}: compose", flush=True)
    paths = compose_fresh_paths(cfg, functions, functions[0].function_id)
    print(f"{mode}: {len(paths)} composed paths", flush=True)
    binary.chmod(0o500)
    if hashlib.sha256(binary.read_bytes()).hexdigest() != digest:
        raise RuntimeError("candidate changed after extraction")
    return {"binary": binary, "sha256": digest, "elf_base64": base64.b64encode(raw).decode(),
            "cfg": cfg, "functions": functions, "runner": runner, "paths": paths,
            "root_model": {"cfg": cfg, "fresh_model": functions[0].to_data()}}


def _composed_observation(case: dict, x: int, y: int) -> dict:
    runner = case["runner"]
    state = runner.initial_state((2, 0, 0, x, y), extra_registers={"rdx": STORAGE})
    enabled = [path for path in case["paths"] if eval_expr(QFAbvExpr(runner.context, BoolSort(), path.guard), state)]
    if len(enabled) != 1:
        return {"status": "COMPOSE_INCOMPLETE", "enabled_paths": len(enabled)}
    path = enabled[0]
    update = QFAbvUpdate(runner.context, runner.context, tuple(
        QFAbvExpr(runner.context, decode_sort(declaration.sort), path.update[declaration.name])
        for declaration in runner.context.declarations))
    after = eval_update(update, state)
    values = dict(zip((declaration.name for declaration in runner.context.declarations), after.values))
    if values["rip"] != RETURN:
        return {"status": "COMPOSE_INCOMPLETE", "target": path.target.kind, "rip": values["rip"]}
    memory = dict(values["mem"].entries)
    return {"status": "RETURN", "result": values["rax"],
            "memory": [memory.get(STORAGE + i, values["mem"].default) for i in range(STORAGE_SIZE)],
            "path_id": path.run_id}


def _native_observation(binary: Path, x: int, y: int) -> dict:
    try:
        run = subprocess.run(command(binary, (2, 0, 0, x, y)), text=True,
                             capture_output=True, timeout=5)
    except subprocess.TimeoutExpired:
        return {"status": "NATIVE_INCOMPLETE", "reason": "timeout"}
    if run.returncode:
        return {"status": "NATIVE_INCOMPLETE", "exit": run.returncode,
                "stderr": run.stderr}
    fields = run.stdout.split()
    if len(fields) != STORAGE_SIZE + 1:
        return {"status": "NATIVE_INCOMPLETE", "field_count": len(fields)}
    return {"status": "RETURN", "result": int(fields[0]),
            "memory": [int(value, 16) for value in fields[1:]]}


def compare(first: Path, second: Path, *, samples: int, output: Path) -> dict:
    with tempfile.TemporaryDirectory(prefix="wruh-composition-") as temp:
        base = Path(temp)
        cases = {name: _compile_and_extract(base / name, name, first, second)
                 for name in WRAPPERS}
        # Solved inputs are selected from the two-function composition, then
        # replayed unchanged against the baseline and both identity variants.
        inputs, partitions = solve_samples(cases["two_functions"]["root_model"], samples,
                                           functions=cases["two_functions"]["functions"],
                                           paths=cases["two_functions"]["paths"])
        if not inputs:
            for partition in partitions:
                if partition["status"] != "UNKNOWN":
                    continue
                print(f"isolated SMT retry: path {partition['index']}", flush=True)
                retried_inputs, retried_paths = solve_samples(
                    cases["two_functions"]["root_model"], samples,
                    path_indices={partition["index"]},
                    functions=cases["two_functions"]["functions"],
                    paths=cases["two_functions"]["paths"])
                partition["first_pass"] = {"status": "UNKNOWN", "reason": partition.get("reason")}
                partition.update(status=retried_paths[0]["status"],
                                 samples=retried_paths[0]["samples"],
                                 retry=retried_paths[0])
                inputs.extend(retried_inputs)
                if len(inputs) >= samples:
                    break
        output.with_suffix(".inputs.json").write_text(json.dumps(inputs) + "\n")
        output.with_suffix(".partitions.json").write_text(json.dumps(partitions, indent=2) + "\n")
        results = []
        for sample in inputs:
            x, y = sample["x"], sample["y"]
            observations = {}
            for mode, case in cases.items():
                model = _composed_observation(case, x, y)
                native = _native_observation(case["binary"], x, y)
                observations[mode] = {"model": model, "native": native}
            valid = all(item["model"]["status"] == "RETURN" and
                        item["native"]["status"] == "RETURN" and
                        (item["model"]["result"], item["model"]["memory"]) ==
                        (item["native"]["result"], item["native"]["memory"])
                        for item in observations.values())
            plain = observations["plain"]["native"]
            identities = all(observations[name]["native"] == plain and
                             observations[name]["model"]["result"] == observations["plain"]["model"]["result"] and
                             observations[name]["model"]["memory"] == observations["plain"]["model"]["memory"]
                             for name in ("left_identity", "right_identity"))
            record = {"x": x, "y": y, "status": "MATCH" if valid and identities else "MISMATCH_OR_INCOMPLETE"}
            if record["status"] != "MATCH":
                record["observations"] = observations
            results.append(record)
            with output.with_suffix(".progress.jsonl").open("a") as stream:
                stream.write(json.dumps(record, separators=(",", ":")) + "\n")
        return {"status": "MATCH" if len(results) == samples and all(item["status"] == "MATCH" for item in results)
                else "INCOMPLETE_OR_MISMATCH", "requested_samples": samples,
                "completed_samples": len(results), "partitions": partitions,
                "binaries": {name: case["sha256"] for name, case in cases.items()},
                "results": results}


def run_campaign(isa: Path, config: Path, output: Path, *, pairs: int,
                 samples: int, seed: int) -> dict:
    """Generate fresh programs on demand, then check every adjacent pair."""
    source = os.environ.get("WRUH_REVIZOR_SOURCE")
    python = os.environ.get("WRUH_REVIZOR_PYTHON")
    if not source or not python:
        raise RuntimeError("the pinned Revizor source and Python must be in the development shell")
    effective_seed = seed if seed else (secrets.randbits(32) or 1)
    output.mkdir(parents=True, exist_ok=False)
    programs = output / "programs"
    environment = os.environ.copy()
    environment["PYTHONPATH"] = source
    subprocess.run([python, str(Path(__file__).with_name("revizor_generate.py")),
                    "--isa", str(isa), "--config", str(config),
                    "--output", str(programs), "--count", str(2 * pairs),
                    "--seed", str(effective_seed)], check=True, env=environment)
    manifest = {"schema": "wruh-revizor-composition-campaign-v1",
                "isa": str(isa), "config": config.read_text(),
                "seed": effective_seed, "pairs": pairs, "samples_per_pair": samples}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    outcomes = []
    for index in range(pairs):
        first = programs / f"case-{2 * index}" / "program.asm"
        second = programs / f"case-{2 * index + 1}" / "program.asm"
        result_path = output / f"pair-{index}.json"
        print(f"pair {index + 1}/{pairs}: generated programs {2 * index} and {2 * index + 1}", flush=True)
        try:
            result = compare(first, second, samples=samples, output=result_path)
        except Exception as error:
            result = {"status": "INCOMPLETE", "error_type": type(error).__name__,
                      "error": str(error)}
        result_path.write_text(json.dumps(result, indent=2) + "\n")
        record = {"pair": index, "status": result["status"],
                  "completed_samples": result.get("completed_samples", 0)}
        outcomes.append(record)
        with (output / "progress.jsonl").open("a") as stream:
            stream.write(json.dumps(record, separators=(",", ":")) + "\n")
        print(f"pair {index + 1}/{pairs}: {record['status']} ({record['completed_samples']}/{samples})", flush=True)
    summary = {**manifest, "status": "MATCH" if all(item["status"] == "MATCH" for item in outcomes)
               else "INCOMPLETE_OR_MISMATCH", "outcomes": outcomes}
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--isa", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="new evidence directory")
    parser.add_argument("--pairs", type=int, default=10)
    parser.add_argument("--samples", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=0, help="0 chooses and records a random seed")
    args = parser.parse_args()
    if args.samples < 1 or args.pairs < 1 or args.seed < 0:
        parser.error("pairs and samples must be positive; seed must be nonnegative")
    if args.output.exists():
        parser.error("output directory already exists")
    result = run_campaign(args.isa, args.config, args.output,
                          pairs=args.pairs, samples=args.samples, seed=args.seed)
    print(result["status"])
    if result["status"] != "MATCH":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
