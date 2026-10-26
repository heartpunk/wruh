"""Focused contracts for AMD64 finite-selector register reads."""
from types import SimpleNamespace
import unittest

from extractor.amd64_state import (
    Amd64AdapterError,
    _SelectorSplitRequired,
    _selector_read_hook,
)


class _SymbolicOffset:
    op = "Add"
    args = ()

    def __init__(self, *variables):
        self.variables = frozenset(variables)


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

    def test_unassigned_ftop_offset_requests_finite_domain_split(self):
        with self.assertRaises(_SelectorSplitRequired) as raised:
            _selector_read_hook(self._state(_SymbolicOffset("ftop")))
        self.assertEqual(raised.exception.name, "ftop")

    def test_assigned_modular_ftop_offset_is_accepted(self):
        _selector_read_hook(
            self._state(_SymbolicOffset("ftop"), {"ftop": 3})
        )

    def test_unknown_or_mixed_symbolic_offsets_fail_closed(self):
        for offset in (_SymbolicOffset("other"), _SymbolicOffset("ftop", "other")):
            with self.subTest(variables=offset.variables):
                with self.assertRaises(Amd64AdapterError):
                    _selector_read_hook(self._state(offset))


if __name__ == "__main__":
    unittest.main()
