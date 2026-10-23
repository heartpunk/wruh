"""Exercise end-of-symbol calls through the public CLI using a tiny ELF."""

from extractor.runtime_trace import start_runtime_trace

start_runtime_trace()
from extractor.native_runtime import preload_libstdcxx

preload_libstdcxx()

import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile

import z3
from ayxg.codec import loads
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
    ("direct_end", 0, b"\xe8" + struct.pack("<i", EXTERNAL - (BASE + TEXT_OFFSET + 5)), True),
    ("indirect_end", 16, b"\xff\xd0", True),
    ("direct_in_range", 32, b"\xe8" + struct.pack("<i", EXTERNAL - (BASE + TEXT_OFFSET + 37)) + b"\xc3", True),
    ("indirect_in_range", 48, b"\xff\xd0\xc3", True),
    ("strict_boundary", 64, b"\xe8" + struct.pack("<i", BASE + TEXT_OFFSET + 80 - (BASE + TEXT_OFFSET + 69)), True),
    ("strict_target", 80, b"\xc3", False),
)
CLI_ROOTS = ("direct_end", "indirect_end", "direct_in_range", "indirect_in_range")


def write_fixture(path: Path) -> None:
    """Write a valid ELF64 with executable bytes and sized function symbols."""
    text = bytearray(b"\x90" * 81)
    strings = bytearray(b"\0")
    symbols = bytearray(24)
    for name, offset, code, _ in FIXTURES:
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


def check_call(function_data: dict, name: str, address: int, return_pc: int, symbolic: bool) -> None:
    function = FreshFunction.from_data(function_data)
    edge = next(edge for edge in function.local_edges if edge.source == address)
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
    expected_guard = variables["rip"] == address

    def assert_unsat(condition: z3.BoolRef, detail: str) -> None:
        solver = z3.Solver(ctx=context)
        solver.add(condition)
        assert solver.check() == z3.unsat, (name, detail, solver)

    assert set(actual) == set(variables), name
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
    witness.add(guard, variables["rsp"] == 0x800008, variables["rax"] == EXTERNAL)
    assert witness.check() == z3.sat, (name, "feasible call edge")
    model = witness.model()
    assert model.eval(actual["rip"]).as_long() == EXTERNAL, name
    assert model.eval(actual["rsp"]).as_long() == 0x800000, name


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
        roots = bundle["cfg"]["roots"]
        functions = {item["function_id"]: item for item in bundle["functions"]}

        for name, _, code, _ in FIXTURES[:4]:
            root = roots[name]
            address = root["address"]
            instructions = [instruction for block in root["blocks"] for instruction in block["instructions"]]
            call = instructions[0]
            assert call["address"] == address and call["size"] == (2 if name.startswith("indirect") else 5)
            assert len(root["calls"]) == 1 and root["calls"][0]["kind"] == "open", name
            assert root["calls"][0]["target"] == (None if name.startswith("indirect") else EXTERNAL), name
            if name.endswith("_end"):
                assert call["address"] + call["size"] == address + root["size"], name
                assert root["blocks"][-1]["successors"] == [], name
            else:
                assert any(
                    instruction["address"] == address + len(code) - 1 and instruction["mnemonic"] == "ret"
                    for instruction in instructions
                ), name
                assert root["blocks"][0]["successors"] == [address + call["size"]], name
            check_call(functions[name], name, address, address + call["size"], name.startswith("indirect"))

        # A direct call to a selected local target keeps strict-mode validation
        # of its out-of-extent continuation, while open mode can retain it.
        project = load_object_set(artifact)
        strict_policy = exact_symbol_inventory_policy(("strict_boundary", "strict_target"), open_transfers=False)
        strict_manifest = inventory_project(project, artifact, strict_policy)
        try:
            build_static_cfg(PinnedBinary(artifact, strict_manifest, project))
        except InventoryError:
            pass
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
        except InventoryError:
            pass
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
