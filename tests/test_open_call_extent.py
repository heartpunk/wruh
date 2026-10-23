"""Exercise end-of-symbol calls through the public CLI using a tiny ELF."""

from extractor.runtime_trace import start_runtime_trace

start_runtime_trace()
from extractor.native_runtime import preload_libstdcxx

preload_libstdcxx()

import hashlib
import json
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

import z3
from ayxg.codec import loads
from ayxg.expr import TermSort
from ayxg.z3 import declaration_variables, expr_to_z3

from extractor.binary_cfg import build_static_cfg
from extractor.binary_inventory import (
    InventoryError,
    PinnedBinary,
    exact_symbol_inventory_policy,
    inventory_project,
)
from extractor.fresh import FreshFunction
from extractor.loaded_image import load_object_set

BASE = 0x400000
TEXT_OFFSET = 0x1000
EXTERNAL = 0x70000000
FIXTURES = (
    ("direct_end", 0, b"\xe8" + struct.pack("<i", EXTERNAL - (BASE + TEXT_OFFSET + 5))),
    ("indirect_end", 16, b"\xff\xd0"),
    ("direct_in_range", 32, b"\xe8" + struct.pack("<i", EXTERNAL - (BASE + TEXT_OFFSET + 37)) + b"\xc3"),
    ("indirect_in_range", 48, b"\xff\xd0\xc3"),
    ("strict_boundary", 64, b"\xe8" + struct.pack("<i", BASE + TEXT_OFFSET + 80 - (BASE + TEXT_OFFSET + 69))),
    ("strict_target", 80, b"\xc3"),
)
CLI_ROOTS = ("direct_end", "indirect_end", "direct_in_range", "indirect_in_range")
CALL_SIZES = {"direct": 5, "indirect": 2}
# Independent sort contract for this pinned AMD64 runtime. Do not derive this
# oracle from extracted declarations or production architecture helpers.
AMD64_SORTS = {
    **dict.fromkeys(
        (
            "rax", "rcx", "rdx", "rbx", "rsp", "rbp", "rsi", "rdi",
            "r8", "r9", "r10", "r11", "r12", "r13", "r14", "r15",
            "d", "rip", "ac", "id", "fs", "sseround", "cr0", "cr2",
            "cr3", "cr4", "cr8", "fptag", "fpround", "fc3210", "cmstart",
            "cmlen", "nraddr", "gs", "ip_at_syscall",
        ),
        TermSort.bv(64),
    ),
    **{f"zmm{index}": TermSort.bv(512) for index in range(32)},
    **{f"k{index}": TermSort.bv(64) for index in range(8)},
    "ftop": TermSort.bv(32),
    "emnote": TermSort.bv(32),
    "fpreg": TermSort.bv(512),
    **{
        f"{segment}_seg": TermSort.bv(16)
        for segment in ("cs", "ds", "es", "fs", "gs", "ss")
    },
    **{
        f"rflags_{flag}": TermSort.bv(1)
        for flag in ("CF", "ZF", "SF", "OF", "PF", "AF")
    },
    "mem": TermSort.array(64, 8),
}
assert len(AMD64_SORTS) == 91


def write_fixture(path: Path) -> None:
    """Write a valid ELF64 with executable bytes and sized function symbols."""
    text = bytearray(b"\x90" * 81)
    strings = bytearray(b"\0")
    symbols = bytearray(24)
    for name, offset, code in FIXTURES:
        text[offset : offset + len(code)] = code
        name_offset = len(strings)
        strings.extend(name.encode() + b"\0")
        symbols.extend(
            struct.pack("<IBBHQQ", name_offset, 0x12, 0, 1, BASE + TEXT_OFFSET + offset, len(code))
        )
    section_names = b"\0.text\0.symtab\0.strtab\0.shstrtab\0"
    sym_offset = (TEXT_OFFSET + len(text) + 7) & ~7
    str_offset = sym_offset + len(symbols)
    names_offset = str_offset + len(strings)
    sections_offset = (names_offset + len(section_names) + 7) & ~7
    raw = bytearray(sections_offset + 5 * 64)
    ident = b"\x7fELF\x02\x01\x01" + bytes(9)
    raw[:64] = struct.pack(
        "<16sHHIQQQIHHHHHH",
        ident,
        2,
        62,
        1,
        BASE + TEXT_OFFSET,
        64,
        sections_offset,
        0,
        64,
        56,
        1,
        64,
        5,
        4,
    )
    raw[64:120] = struct.pack(
        "<IIQQQQQQ", 1, 5, 0, BASE, BASE, TEXT_OFFSET + len(text), TEXT_OFFSET + len(text), 0x1000
    )
    raw[TEXT_OFFSET : TEXT_OFFSET + len(text)] = text
    raw[sym_offset : sym_offset + len(symbols)] = symbols
    raw[str_offset : str_offset + len(strings)] = strings
    raw[names_offset : names_offset + len(section_names)] = section_names
    sections = (
        (1, 1, 6, BASE + TEXT_OFFSET, TEXT_OFFSET, len(text), 0, 0, 16, 0),
        (7, 2, 0, 0, sym_offset, len(symbols), 3, 1, 8, 24),
        (15, 3, 0, 0, str_offset, len(strings), 0, 0, 1, 0),
        (23, 3, 0, 0, names_offset, len(section_names), 0, 0, 1, 0),
    )
    for index, section in enumerate(sections, 1):
        start = sections_offset + index * 64
        raw[start : start + 64] = struct.pack("<IIQQQQIIQQ", *section)
    path.write_bytes(raw)


def check_call(
    function_data: dict,
    name: str,
    source_address: int,
    return_pc: int,
    symbolic: bool,
    expected_instruction_addresses: tuple[int, ...],
) -> None:
    function = FreshFunction.from_data(function_data)
    source_edges = [
        edge for edge in function.local_edges if edge.source == source_address
    ]
    occurrence_addresses = tuple(
        sorted(item.origin.canonical_address for item in function.occurrences)
    )
    edge_sources = tuple(sorted(edge.source for edge in function.local_edges))
    assert occurrence_addresses == expected_instruction_addresses, (
        name, "complete occurrence roster", occurrence_addresses,
    )
    assert edge_sources == expected_instruction_addresses, (
        name, "complete edge source roster", edge_sources,
    )
    assert len(source_edges) == 1, (name, source_edges)
    edge = source_edges[0]
    context = z3.Context()
    variables = declaration_variables(function.declarations, context)
    actual = {
        assignment.name: expr_to_z3(assignment.value, variables, context)
        for assignment in edge.summary.simultaneous_update
    }
    expected = dict(variables)
    target = variables["rax"] if symbolic else z3.BitVecVal(EXTERNAL, 64, ctx=context)
    expected["rip"] = target
    expected["rsp"] = variables["rsp"] - z3.BitVecVal(8, 64, ctx=context)
    memory = variables["mem"]
    for offset in range(8):
        byte = z3.BitVecVal((return_pc >> (8 * offset)) & 0xFF, 8, ctx=context)
        memory = z3.Store(memory, expected["rsp"] + offset, byte)
    expected["mem"] = memory
    guard = expr_to_z3(edge.summary.guard, variables, context)
    expected_guard = variables["rip"] == source_address

    def assert_unsat(condition: z3.BoolRef, detail: str) -> None:
        solver = z3.Solver(ctx=context)
        solver.add(condition)
        solver.set(timeout=5000)
        assert solver.check() == z3.unsat, (name, detail, solver)

    assert len(function.declarations) == 91, (name, "declaration count")
    assert {item.name: item.sort for item in function.declarations} == AMD64_SORTS, (
        name, "AMD64 state contract",
    )
    assert set(actual) == set(variables) == set(AMD64_SORTS), name
    assert_unsat(z3.Xor(guard, expected_guard), "exact source guard")
    for variable in variables:
        assert_unsat(z3.And(guard, actual[variable] != expected[variable]), "full poststate: " + variable)
    assert edge.summary.target.kind == ("symbolic" if symbolic else "address"), name
    if symbolic:
        assert_unsat(expr_to_z3(edge.summary.target.value, variables, context) != target, "symbolic target")
    else:
        assert edge.summary.target.value == EXTERNAL, name
    assert_unsat(expr_to_z3(edge.summary.mirrored_pc, variables, context) != target, "mirrored PC")
    witness = z3.Solver(ctx=context)
    witness.set(timeout=5000)
    witness.add(guard, variables["rsp"] == 0x800008, variables["rax"] == EXTERNAL)
    assert witness.check() == z3.sat, (name, "feasible call edge")
    model = witness.model()
    assert model.eval(actual["rip"]).as_long() == EXTERNAL, name
    assert model.eval(actual["rsp"]).as_long() == 0x800000, name


def check_return(
    function_data: dict,
    name: str,
    source_address: int,
    expected_instruction_addresses: tuple[int, ...],
) -> None:
    function = FreshFunction.from_data(function_data)
    source_edges = [
        edge for edge in function.local_edges if edge.source == source_address
    ]
    occurrence_addresses = tuple(
        sorted(item.origin.canonical_address for item in function.occurrences)
    )
    edge_sources = tuple(sorted(item.source for item in function.local_edges))
    assert occurrence_addresses == expected_instruction_addresses, (
        name, "RET occurrence roster", occurrence_addresses,
    )
    assert edge_sources == expected_instruction_addresses, (
        name, "RET edge source roster", edge_sources,
    )
    assert len(source_edges) == 1, (name, "RET edge", source_edges)
    edge = source_edges[0]
    context = z3.Context()
    variables = declaration_variables(function.declarations, context)
    actual = {
        assignment.name: expr_to_z3(assignment.value, variables, context)
        for assignment in edge.summary.simultaneous_update
    }
    return_address = 0x500123
    old_rsp = variables["rsp"]
    target = z3.Concat(*(
        z3.Select(variables["mem"], old_rsp + offset)
        for offset in reversed(range(8))
    ))
    expected = dict(variables)
    expected["rip"] = target
    expected["rsp"] = old_rsp + 8
    guard = expr_to_z3(edge.summary.guard, variables, context)
    expected_guard = variables["rip"] == source_address

    def assert_unsat(condition: z3.BoolRef, detail: str) -> None:
        solver = z3.Solver(ctx=context)
        solver.set(timeout=5000)
        solver.add(condition)
        assert solver.check() == z3.unsat, (name, detail, solver)

    assert len(function.declarations) == 91, (name, "declaration count")
    assert {item.name: item.sort for item in function.declarations} == AMD64_SORTS, (
        name, "AMD64 state contract",
    )
    assert set(actual) == set(variables) == set(AMD64_SORTS), name
    assert_unsat(z3.Xor(guard, expected_guard), "RET source guard")
    for variable in variables:
        assert_unsat(
            z3.And(guard, actual[variable] != expected[variable]),
            "RET full poststate: " + variable,
        )
    assert edge.summary.target.kind == "symbolic", name
    assert_unsat(
        expr_to_z3(edge.summary.target.value, variables, context) != target,
        "RET loads its target from old RSP",
    )
    assert_unsat(
        expr_to_z3(edge.summary.mirrored_pc, variables, context) != target,
        "RET mirrored PC",
    )
    memory = variables["mem"]
    for offset in range(8):
        memory = z3.Store(
            memory,
            old_rsp + offset,
            z3.BitVecVal((return_address >> (8 * offset)) & 0xFF, 8, ctx=context),
        )
    witness = z3.Solver(ctx=context)
    witness.set(timeout=5000)
    witness.add(guard, old_rsp == 0x800000, variables["mem"] == memory)
    assert witness.check() == z3.sat, (name, "feasible RET edge")
    model = witness.model()
    assert model.eval(actual["rip"]).as_long() == return_address, name
    assert model.eval(actual["rsp"]).as_long() == 0x800008, name


def main() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        directory = Path(temporary)
        artifact = directory / "open-call-boundary.elf"
        output = directory / "bundle.json"
        write_fixture(artifact)
        command = [sys.executable, "-m", "extractor.extract_cli", "--artifact", str(artifact), "--root", CLI_ROOTS[0], "--root-only"]
        for candidate in CLI_ROOTS[1:]:
            command.extend(("--candidate-root", candidate))
        command.extend(("--output", str(output)))
        subprocess.run(command, check=True)
        bundle = loads(output.read_text(encoding="utf-8"))
        project = load_object_set(artifact)
        for symbol_name, _, code in FIXTURES:
            symbol = project.loader.main_object.get_symbol(symbol_name)
            assert symbol is not None and symbol.size == len(code), symbol_name
        roots = bundle["cfg"]["roots"]
        functions = {item["function_id"]: item for item in bundle["functions"]}

        for name, offset, code in FIXTURES[:4]:
            root = roots[name]
            address = BASE + TEXT_OFFSET + offset
            assert root["address"] == address, name
            instructions = [
                instruction
                for block in root["blocks"]
                for instruction in block["instructions"]
            ]
            call = instructions[0]
            call_size = CALL_SIZES[
                "indirect" if name.startswith("indirect") else "direct"
            ]
            expected_instruction_addresses = (
                (address,) if name.endswith("_end")
                else (address, address + call_size)
            )
            assert tuple(item["address"] for item in instructions) == (
                expected_instruction_addresses
            ), name
            assert call["address"] == address and call["size"] == call_size
            assert len(root["calls"]) == 1 and root["calls"][0]["kind"] == "open", name
            assert root["calls"][0]["target"] == (None if name.startswith("indirect") else EXTERNAL), name
            if name.endswith("_end"):
                assert address + call_size == address + root["size"], name
                assert root["blocks"][-1]["successors"] == [], name
            else:
                assert any(
                    instruction["address"] == address + len(code) - 1 and instruction["mnemonic"] == "ret"
                    for instruction in instructions
                ), name
                assert root["blocks"][0]["successors"] == [address + call["size"]], name
            check_call(
                functions[name], name, address, address + call_size,
                name.startswith("indirect"), expected_instruction_addresses,
            )
            if not name.endswith("_end"):
                check_return(
                    functions[name], name, address + call_size,
                    expected_instruction_addresses,
                )

        # A direct call to a selected local target keeps strict-mode validation
        # of its out-of-extent continuation, while open mode can retain it.
        strict_policy = exact_symbol_inventory_policy(("strict_boundary", "strict_target"), open_transfers=False)
        strict_manifest = inventory_project(project, artifact, strict_policy)
        try:
            build_static_cfg(PinnedBinary(artifact, strict_manifest, project))
        except InventoryError as error:
            assert "call fallthrough leaves the function" in str(error), error
        else:
            raise AssertionError("strict mode accepted an out-of-extent call continuation")

        open_policy = exact_symbol_inventory_policy(("direct_end",), open_transfers=True, discover_direct_targets=False)
        open_manifest = inventory_project(project, artifact, open_policy)
        truncated_manifest = {
            **open_manifest,
            "roots": {name: dict(root) for name, root in open_manifest["roots"].items()},
        }
        truncated_manifest["roots"]["direct_end"]["size"] -= 1
        try:
            build_static_cfg(PinnedBinary(artifact, truncated_manifest, project))
        except InventoryError as error:
            assert "block at 0x401000 leaves its extent" in str(error), error
        else:
            raise AssertionError("a truncated call instruction was accepted")

        print(json.dumps({
            "pipeline": "compiler-free ELF / public CLI / serialized bundle",
            "end_extent_calls": ["direct", "indirect"],
            "in_range_continuations": ["direct", "indirect"],
            "strict_mode": "rejected",
            "truncated_instruction": "rejected",
            "artifact_sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
            "native_execution": False,
        }, sort_keys=True))


if __name__ == "__main__":
    main()
