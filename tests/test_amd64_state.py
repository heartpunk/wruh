"""Focused contracts for AMD64 finite-selector register reads."""
from types import SimpleNamespace
import unittest

from extractor.amd64_state import (
    Amd64AdapterError,
    _SelectorSplitRequired,
    _selector_read_hook,
)
from extractor.runtime import claripy


class SelectorReadHookTests(unittest.TestCase):
    @staticmethod
    def _state(offset, assignments=None):
        return SimpleNamespace(
            globals={
                "_wruh_capture_selectors": True,
                "_wruh_selector_assignments": assignments or {},
            },
            inspect=SimpleNamespace(reg_read_offset=offset),
        )

    @staticmethod
    def _ftop_offset():
        ftop = claripy.BVS("ftop", 64, explicit_name=True)
        return claripy.BVV(0x100, 64) + ((ftop & claripy.BVV(7, 64)) << 3)

    def test_unassigned_symbolic_ftop_offset_requests_finite_domain_split(self):
        with self.assertRaises(_SelectorSplitRequired) as raised:
            _selector_read_hook(self._state(self._ftop_offset()))
        self.assertEqual(raised.exception.name, "ftop")

    def test_assigned_modular_ftop_offset_is_accepted(self):
        _selector_read_hook(
            self._state(self._ftop_offset(), {"ftop": 3})
        )

    def test_unknown_or_mixed_symbolic_offsets_fail_closed(self):
        ftop = claripy.BVS("ftop", 64, explicit_name=True)
        other = claripy.BVS("other", 64, explicit_name=True)
        for offset in (other, ftop + other):
            with self.subTest(variables=offset.variables):
                with self.assertRaises(Amd64AdapterError):
                    _selector_read_hook(self._state(offset))

    def test_assigned_nonmodular_selector_must_become_concrete(self):
        sseround = claripy.BVS("sseround", 64, explicit_name=True)
        with self.assertRaisesRegex(Amd64AdapterError, "remained symbolic after splitting"):
            _selector_read_hook(self._state(sseround, {"sseround": 2}))


if __name__ == "__main__":
    unittest.main()
