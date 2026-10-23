"""Exercise calls at function extent boundaries through the public CLI."""

from extractor.runtime_trace import start_runtime_trace

start_runtime_trace()

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from extractor.binary_cfg import build_static_cfg
from extractor.binary_inventory import InventoryError, PinnedBinary, exact_symbol_inventory_policy, inventory_project
from extractor.loaded_image import load_object_set



def main() -> None:
    compiler = shutil.which("clang")
    if compiler is None:
        raise RuntimeError("declared clang runtime absent")

    with tempfile.TemporaryDirectory() as temp:
        directory = Path(temp)
        source = directory / "calls.c"
        artifact = directory / "calls.elf"
        output = directory / "bundle.json"
        source.write_text(
            """
            __attribute__((naked, noinline, used)) void direct_root(void) {
              __asm__("call direct_target");
            }
            __attribute__((naked, noinline, used)) void indirect_root(void) {
              __asm__("call *%rax");
            }
            __attribute__((naked, noinline, used)) void in_range_root(void) {
              __asm__("call direct_target\\n\\tret");
            }
            __attribute__((naked, noinline, used)) void direct_target(void) {
              __asm__("ret");
            }
            """,
            encoding="utf-8",
        )
        subprocess.run(
            [compiler, "-O0", "-nostdlib", "-no-pie", "-Wl,-e,direct_root", str(source), "-o", str(artifact)],
            check=True,
        )
        command = [
            sys.executable,
            "-m",
            "extractor.extract_cli",
            "--artifact",
            str(artifact),
            "--root",
            "direct_root",
            "--root-only",
            "--candidate-root",
            "indirect_root",
            "--candidate-root",
            "in_range_root",
            "--candidate-root",
            "direct_target",
            "--output",
            str(output),
        ]
        subprocess.run(command, check=True)
        bundle = json.loads(output.read_text(encoding="utf-8"))
        roots = bundle["cfg"]["roots"]
        functions = {item["function_id"]: item for item in bundle["functions"]}

        direct = roots["direct_root"]
        direct_call = direct["calls"][0]
        assert direct_call["kind"] == "open"
        assert direct_call["target"] == roots["direct_target"]["address"]
        assert direct["blocks"][-1]["successors"] == []
        direct_edges = [edge for edge in functions["direct_root"]["local_edges"] if edge["source"] == direct_call["address"]]
        assert direct_edges, "direct call has no feasible extracted edge"

        indirect = roots["indirect_root"]
        indirect_call = indirect["calls"][0]
        assert indirect_call["kind"] == "open" and indirect_call["target"] is None
        indirect_edges = [edge for edge in functions["indirect_root"]["local_edges"] if edge["source"] == indirect_call["address"]]
        assert indirect_edges, "indirect call has no feasible extracted edge"

        def assert_call_frame(edge: dict, next_pc: int) -> None:
            updates = edge["summary"]["simultaneous_update"]
            update = {item["name"]: item["value"] for item in updates}
            assert update["rsp"]["op"] == "bv_sub"
            assert update["rsp"]["args"][0]["op"] == "var"
            assert update["rsp"]["args"][0]["name"] == "rsp"
            assert update["rsp"]["args"][1]["op"] == "bv_lit"
            assert update["rsp"]["args"][1]["value"] == 8
            assert update["rip"]["op"] == "bv_lit" and update["rip"]["value"] == next_pc
            memory = update["mem"]
            stores = []
            pending = [memory]
            while pending:
                expression = pending.pop()
                pending.extend(expression.get("args", ()))
                if expression["op"] == "store":
                    stores.append(expression)
            assert stores, "call did not store its return address in memory"
            offsets = set()
            for store in stores:
                address = store["args"][1]
                if address == update["rsp"]:
                    offset = 0
                elif address["op"] == "bv_add" and address["args"][0] == update["rsp"]:
                    offset = address["args"][1].get("value")
                else:
                    continue
                value = store["args"][2]
                if (
                    type(offset) is int
                    and 0 <= offset < 8
                    and value["op"] == "extract"
                    and value["args"][0]["op"] == "bv_lit"
                    and value["args"][0]["value"] == next_pc
                    and value["lo"] == offset * 8
                    and value["hi"] == offset * 8 + 7
                ):
                    offsets.add(offset)
            assert offsets == set(range(8)), "return-address bytes were not stored at the decremented stack pointer"

        assert_call_frame(direct_edges[0], direct_call["address"] + 5)
        assert_call_frame(indirect_edges[0], indirect_call["address"] + 2)

        in_range = roots["in_range_root"]
        assert in_range["blocks"][0]["successors"] == [in_range["blocks"][1]["address"]]
        assert len(in_range["blocks"]) > 1

        # Keep the original validation boundaries: strict inventories reject
        # an out-of-extent call continuation, and a truncated call cannot be
        # admitted as a complete instruction.
        project = load_object_set(artifact)
        open_manifest = inventory_project(
            project,
            artifact,
            exact_symbol_inventory_policy(("direct_root", "direct_target"), open_transfers=True, discover_direct_targets=False),
        )
        strict_manifest = dict(open_manifest)
        strict_manifest.pop("open_transfers")
        try:
            build_static_cfg(PinnedBinary(artifact, strict_manifest, project))
        except InventoryError:
            pass
        else:
            raise AssertionError("strict mode accepted out-of-extent call continuation")

        truncated_manifest = json.loads(json.dumps(open_manifest))
        truncated_manifest["roots"]["direct_root"]["size"] -= 1
        try:
            build_static_cfg(PinnedBinary(artifact, truncated_manifest, project))
        except InventoryError:
            pass
        else:
            raise AssertionError("truncated call instruction was accepted")
        result = {
            "direct_end_call": "open transfer and call frame retained",
            "indirect_end_call": "open transfer and call frame retained",
            "in_range_call": "continuation retained",
            "strict_mode": "out-of-extent continuation rejected",
            "truncated_instruction": "rejected",
            "cli": command,
        }
        print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
