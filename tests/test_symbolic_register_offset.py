"""Symbolic register offsets must be fixed before normalizing their access."""

import unittest

from extractor import runtime

angr = runtime.angr
claripy = runtime.claripy

from extractor.amd64_state import (
    Amd64AdapterError,
    _concretize_unique_register_read_offset,
)


class SymbolicRegisterOffsetTests(unittest.TestCase):
    def state(self):
        project = angr.load_shellcode(b"\x90", arch="amd64", load_address=0x400000)
        state = project.factory.blank_state(addr=0x400000)
        state.globals["_wruh_capture_selectors"] = True
        return state

    def test_x87_stack_tag_slot_is_unique_for_every_ftop_selector(self):
        # FILD's x87 tag offset: (FTOP - 1) mod 8, based at VEX's tag array.
        # The selector split knows the low bits but must preserve the high bits.
        for selector in range(8):
            with self.subTest(selector=selector):
                state = self.state()
                ftop = claripy.BVS("ftop_test", 32, explicit_name=True)
                state.add_constraints((ftop & 7) == selector)
                offset = ((ftop - 1) % 8)[31:0] + 0x9A8
                state.inspect.reg_read_offset = offset
                constraints = tuple(state.solver.constraints)
                _concretize_unique_register_read_offset(state)
                self.assertEqual(state.inspect.reg_read_offset, 0x9A8 + ((selector - 1) & 7))
                self.assertEqual(tuple(state.solver.constraints), constraints)
                for upper in (0, 8, 0xFFFFFFF8):
                    self.assertTrue(state.solver.satisfiable(extra_constraints=(ftop == (upper | selector),)))

    def test_ambiguous_offset_is_rejected_without_adding_a_constraint(self):
        state = self.state()
        offset = claripy.BVS("unconstrained_offset", 32, explicit_name=True)
        state.inspect.reg_read_offset = offset
        constraints = tuple(state.solver.constraints)
        with self.assertRaisesRegex(Amd64AdapterError, "cannot identify selector domain"):
            _concretize_unique_register_read_offset(state)
        self.assertIs(state.inspect.reg_read_offset, offset)
        self.assertEqual(tuple(state.solver.constraints), constraints)

    def test_disabled_capture_does_not_change_offset(self):
        state = self.state()
        state.globals["_wruh_capture_selectors"] = False
        offset = claripy.BVS("disabled_offset", 32, explicit_name=True)
        state.inspect.reg_read_offset = offset
        _concretize_unique_register_read_offset(state)
        self.assertIs(state.inspect.reg_read_offset, offset)


if __name__ == "__main__":
    unittest.main()
