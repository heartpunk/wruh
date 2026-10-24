# Collection scripts for WRUH extraction

Run provenance and artifact-recovery status: [[CPython extraction attempt counts]]. Complete exploratory script listings are preserved below.

`extract_all.py` selects sized function symbols, collapses aliases by entry address, writes shared loaded-image metadata, and records each attempted extraction in a success or failure ledger. Shards and the completed ledger make the run resumable.

## `extract_all.py`

```python
#!/usr/bin/env python3
"""Resumable, failure-tolerant Wruh extraction of every sized function symbol."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import json
from pathlib import Path
import traceback

from ayxg.codec import dumps
from extractor.binary_cfg import build_static_cfg
from extractor.binary_inventory import PinnedBinary
from extractor.fresh import extract_fresh_function
from extractor.loaded_image import load_object_set, loaded_image_data


def write_json(path: Path, value: object) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--shard-count", type=int, default=1)
    parser.add_argument("--shard-index", type=int, default=0)
    args = parser.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)
    models = args.output / "models"
    models.mkdir(exist_ok=True)
    if not 1 <= args.shard_count or not 0 <= args.shard_index < args.shard_count:
        parser.error("shard index must be within shard count")
    suffix = "" if args.shard_index == 0 else f".shard-{args.shard_index}"
    failures_path = args.output / f"failures{suffix}.jsonl"
    successes_path = args.output / f"successes{suffix}.jsonl"

    artifact = args.artifact.resolve()
    image_sha256 = hashlib.sha256(artifact.read_bytes()).hexdigest()
    project = load_object_set(artifact)
    image_path = args.output / "loaded-image.json.gz"
    if not image_path.exists():
        with gzip.open(image_path, "wt", encoding="utf-8") as stream:
            json.dump(loaded_image_data(project), stream, sort_keys=True)

    function_symbols = [
        symbol for symbol in project.loader.main_object.symbols
        if symbol.name and symbol.size > 0
        and getattr(getattr(symbol, "type", None), "name", "") == "TYPE_FUNCTION"
    ]
    by_address: dict[int, list[object]] = defaultdict(list)
    for symbol in function_symbols:
        by_address[symbol.rebased_addr].append(symbol)
    name_addresses: dict[str, set[int]] = defaultdict(set)
    for symbol in function_symbols:
        name_addresses[symbol.name].add(symbol.rebased_addr)

    candidates = []
    exclusions = []
    for address, aliases in sorted(by_address.items()):
        names = sorted({symbol.name for symbol in aliases})
        usable = [name for name in names if len(name_addresses[name]) == 1]
        if not usable:
            exclusions.append({
                "address": address,
                "names": names,
                "reason": "every symbol name is defined at multiple addresses",
            })
            continue
        name = usable[0]
        symbol = max(
            (item for item in aliases if item.name == name),
            key=lambda item: item.size,
        )
        candidates.append((name, symbol, names))

    all_candidates = candidates
    if args.shard_index == 0:
        write_json(args.output / "inventory.json", {
        "schema": "wruh-all-functions-inventory-v1",
        "artifact": str(artifact),
        "image_sha256": image_sha256,
        "raw_sized_function_symbols": len(function_symbols),
        "candidate_addresses": len(all_candidates),
        "excluded_ambiguous_addresses": exclusions,
        "selection": "one deterministic unique symbol name per function address",
        })
    candidates = all_candidates[args.shard_index::args.shard_count]
    if args.limit is not None:
        candidates = candidates[:args.limit]

    completed = set()
    for ledger in (failures_path, successes_path):
        if ledger.exists():
            for line in ledger.read_text().splitlines():
                if line:
                    completed.add(json.loads(line)["function_id"])

    counts = Counter(skipped_existing=len(completed))
    for index, (name, symbol, aliases) in enumerate(candidates, 1):
        if name in completed:
            continue
        root = {
            "address": symbol.rebased_addr,
            "size": symbol.size,
            "symbol": name,
            "image_sha256": image_sha256,
            "object_path": str(artifact),
        }
        manifest = {
            "arch": project.arch.name,
            "bits": project.arch.bits,
            "call_graph": {name: {}},
            "image_sha256": image_sha256,
            "indirect_jumps": {},
            "open_transfers": True,
            "pic": bool(project.loader.main_object.pic),
            "primitive_boundaries": {},
            "roots": {name: root},
            "schema": 1,
        }
        try:
            pinned = PinnedBinary(artifact, manifest, project)
            cfg = build_static_cfg(pinned)
            function = extract_fresh_function(pinned, cfg, name)
            bundle = {
                "schema": "wruh-fresh-bundle-v1",
                "image_sha256": image_sha256,
                "root_id": name,
                "cfg": cfg,
                "functions": [function.to_data()],
                "external_edges": [],
                "loaded_image_reference": "../loaded-image.json.gz",
            }
            destination = models / f"{symbol.rebased_addr:016x}.json.gz"
            with gzip.open(destination, "wt", encoding="utf-8") as stream:
                stream.write(dumps(bundle, indent=2, sort_keys=True) + "\n")
            record = {
                "function_id": name,
                "address": symbol.rebased_addr,
                "size": symbol.size,
                "aliases": aliases,
                "occurrences": len(function.occurrences),
                "local_edges": len(function.local_edges),
                "output": str(destination.relative_to(args.output)),
            }
            with successes_path.open("a") as stream:
                stream.write(json.dumps(record, sort_keys=True) + "\n")
            counts["succeeded"] += 1
        except Exception as error:
            record = {
                "function_id": name,
                "address": symbol.rebased_addr,
                "size": symbol.size,
                "aliases": aliases,
                "error_type": type(error).__name__,
                "error": str(error),
                "traceback": traceback.format_exc(),
            }
            with failures_path.open("a") as stream:
                stream.write(json.dumps(record, sort_keys=True) + "\n")
            counts["failed"] += 1
        if index % 25 == 0 or index == len(candidates):
            write_json(args.output / f"progress{suffix}.json", {
                "schema": "wruh-all-functions-progress-v1",
                "shard_count": args.shard_count,
                "shard_index": args.shard_index,
                "total_candidates": len(candidates),
                "processed_this_run": counts["succeeded"] + counts["failed"],
                **counts,
            })
            print(json.dumps({"index": index, "total": len(candidates), **counts}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

`vex_decode_sweep.py` linearly visits executable ELF sections through angr/VEX without constructing a `SimState`. If a larger VEX window fails, it obtains an instruction boundary from Capstone or `objdump`, retries VEX on exactly that instruction, and records a gap only if the retry also fails. Its report counts instruction sites, a different unit from the function-extraction failure table.

## `vex_decode_sweep.py`

```python
#!/usr/bin/env python3
"""Linearly decode every executable section of an ELF through angr/VEX.

This deliberately creates no SimState and performs no execution.  GNU objdump
is used only as a length/mnemonic oracle when both VEX and Capstone refuse an
instruction, so the sweep can resume at the next real instruction boundary.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import time
from collections import Counter
from pathlib import Path

import angr
import pyvex


OBJDUMP_LINE = re.compile(
    r"^\s*([0-9a-fA-F]+):\s+((?:[0-9a-fA-F]{2}\s+)+)\s*(.*?)\s*$"
)


def objdump_one(binary: str, linked_addr: int) -> tuple[int, str, str]:
    result = subprocess.run(
        [
            "objdump",
            "-D",
            "-w",
            "-M",
            "intel",
            f"--start-address={linked_addr:#x}",
            f"--stop-address={linked_addr + 15:#x}",
            binary,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    for line in result.stdout.splitlines():
        match = OBJDUMP_LINE.match(line)
        if match and int(match.group(1), 16) == linked_addr:
            raw = bytes.fromhex(match.group(2))
            asm = match.group(3).strip()
            mnemonic = asm.split(None, 1)[0] if asm else "unknown"
            return len(raw), mnemonic, asm
    return 1, "unknown", "objdump could not decode"


def capstone_one(project: angr.Project, addr: int) -> tuple[int, str, str] | None:
    data = project.loader.memory.load(addr, 15)
    insn = next(iter(project.arch.capstone.disasm(data, addr)), None)
    if insn is None:
        return None
    asm = f"{insn.mnemonic} {insn.op_str}".rstrip()
    return insn.size, insn.mnemonic, asm


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("binary")
    parser.add_argument("output", type=Path)
    parser.add_argument("--progress-seconds", type=float, default=20.0)
    args = parser.parse_args()

    started = time.monotonic()
    project = angr.Project(args.binary, auto_load_libs=False)
    obj = project.loader.main_object
    executable_sections = [
        section for section in obj.sections if getattr(section, "is_executable", False)
    ]

    gaps: list[dict[str, object]] = []
    special_terminators: list[dict[str, object]] = []
    section_reports: list[dict[str, object]] = []
    decoded_instructions = 0
    decoded_bytes = 0
    block_count = 0
    fallback_count = 0
    last_progress = started

    for section in executable_sections:
        addr = section.min_addr
        end = section.max_addr + 1
        section_decoded_instructions = 0
        section_decoded_bytes = 0
        section_gaps = 0

        while addr < end:
            block_count += 1
            # Keep the speculative window small.  Some x86 decoder failures
            # make VEX reject the entire supplied byte window instead of
            # returning the successfully lifted prefix.
            block = project.factory.block(addr, size=min(64, end - addr))
            irsb = block.vex
            imarks = [
                stmt for stmt in irsb.statements if isinstance(stmt, pyvex.stmt.IMark)
            ]
            real_imarks = [stmt for stmt in imarks if stmt.len > 0]
            real_count = len(real_imarks)
            decoded_instructions += real_count
            section_decoded_instructions += real_count

            if irsb.size > 0:
                decoded_bytes += irsb.size
                section_decoded_bytes += irsb.size
                if irsb.jumpkind == "Ijk_NoDecode" and not any(
                    stmt.len == 0 for stmt in imarks
                ):
                    last = real_imarks[-1] if real_imarks else None
                    site = last.addr if last is not None else addr
                    decoded = capstone_one(project, site)
                    special_terminators.append(
                        {
                            "address": site,
                            "section": section.name,
                            "size": last.len if last is not None else irsb.size,
                            "mnemonic": decoded[1] if decoded else "unknown",
                            "assembly": decoded[2] if decoded else "unknown",
                            "jumpkind": irsb.jumpkind,
                        }
                    )
                addr += irsb.size
                continue

            decoded = capstone_one(project, addr)
            decoder = "capstone"
            if decoded is None:
                decoder = "objdump"
                fallback_count += 1
                decoded = objdump_one(args.binary, addr - obj.mapped_base)
            size, mnemonic, assembly = decoded
            size = max(1, min(size, end - addr))
            raw = project.loader.memory.load(addr, size)

            # A later unsupported instruction can cause VEX to reject a
            # larger input window wholesale.  Retry with exactly one oracle-
            # decoded instruction before declaring the current site a gap.
            exact = project.factory.block(addr, size=size).vex
            if exact.size > 0:
                exact_imarks = [
                    stmt
                    for stmt in exact.statements
                    if isinstance(stmt, pyvex.stmt.IMark) and stmt.len > 0
                ]
                exact_count = len(exact_imarks)
                decoded_instructions += exact_count
                section_decoded_instructions += exact_count
                decoded_bytes += exact.size
                section_decoded_bytes += exact.size
                if exact.jumpkind == "Ijk_NoDecode":
                    special_terminators.append(
                        {
                            "address": addr,
                            "section": section.name,
                            "size": exact.size,
                            "mnemonic": mnemonic,
                            "assembly": assembly,
                            "jumpkind": exact.jumpkind,
                        }
                    )
                addr += exact.size
                continue

            gaps.append(
                {
                    "address": addr,
                    "linked_address": addr - obj.mapped_base,
                    "section": section.name,
                    "size": size,
                    "bytes": raw.hex(),
                    "mnemonic": mnemonic,
                    "assembly": assembly,
                    "boundary_decoder": decoder,
                    "vex_jumpkind": irsb.jumpkind,
                }
            )
            section_gaps += 1
            addr += size

            now = time.monotonic()
            if now - last_progress >= args.progress_seconds:
                print(
                    f"{section.name}: {addr - section.min_addr:#x}/{section.memsize:#x} "
                    f"bytes; {decoded_instructions:,} instructions; {len(gaps):,} gaps",
                    flush=True,
                )
                last_progress = now

        section_reports.append(
            {
                "name": section.name,
                "start": section.min_addr,
                "end": end,
                "size": section.memsize,
                "decoded_bytes": section_decoded_bytes,
                "decoded_instructions": section_decoded_instructions,
                "vex_gaps": section_gaps,
            }
        )
        print(
            f"finished {section.name}: {section.memsize:,} bytes, "
            f"{section_decoded_instructions:,} instructions, {section_gaps:,} gaps",
            flush=True,
        )

    elapsed = time.monotonic() - started
    report = {
        "binary": str(Path(args.binary).resolve()),
        "mapped_base": obj.mapped_base,
        "method": (
            "Linear sweep of every SHF_EXECINSTR section using "
            "angr.Project.factory.block; no SimState or execution"
        ),
        "elapsed_seconds": elapsed,
        "sections": section_reports,
        "totals": {
            "executable_bytes": sum(section.memsize for section in executable_sections),
            "vex_decoded_bytes": decoded_bytes,
            "vex_decoded_instructions": decoded_instructions,
            "vex_blocks": block_count,
            "vex_gap_sites": len(gaps),
            "special_nodecode_terminators": len(special_terminators),
            "objdump_boundary_fallbacks": fallback_count,
        },
        "gap_mnemonics": dict(Counter(str(gap["mnemonic"]) for gap in gaps)),
        "gaps": gaps,
        "special_nodecode_terminators": special_terminators,
    }
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(
        f"complete in {elapsed:.1f}s: {decoded_instructions:,} instructions, "
        f"{len(gaps):,} VEX gaps; report={args.output}",
        flush=True,
    )


if __name__ == "__main__":
    main()
```
