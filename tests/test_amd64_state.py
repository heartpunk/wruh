"""Focused contracts for AMD64 finite-selector register reads."""
import math
import struct
from types import SimpleNamespace
import unittest

from extractor.amd64_state import (
    Amd64AdapterError,
    _SelectorSplitRequired,
    _encode_fp_remainder,
    _fp_components,
    _fp_shift_left_bounded,
    _install_x87_fprem_operations,
    _selector_read_hook,
)
from extractor.runtime import claripy


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


class X87PartialRemainderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _install_x87_fprem_operations()
        from angr.engines.vex.claripy.irop import vexop_to_simop

        cls.vexop_to_simop = staticmethod(vexop_to_simop)

    @staticmethod
    def _value(op_name, dividend, divisor):
        op = X87PartialRemainderTests.vexop_to_simop(op_name)
        return op.calculate(
            claripy.FPV(dividend, claripy.FSORT_DOUBLE),
            claripy.FPV(divisor, claripy.FSORT_DOUBLE),
        )

    @staticmethod
    def _evaluate(expression):
        return claripy.Solver().eval(expression, 1)[0]

    @staticmethod
    def _double_bits(value):
        return int.from_bytes(struct.pack(">d", value), "big")

    def test_normal_components_and_remainder_encoding_match_binary64(self):
        dividend = claripy.FPV(5.3, claripy.FSORT_DOUBLE)
        divisor = claripy.FPV(2.0, claripy.FSORT_DOUBLE)
        sign_x, exponent_x, significand_x = _fp_components(dividend)
        _, exponent_y, significand_y = _fp_components(divisor)

        bits_x = self._double_bits(5.3)
        expected_significand_x = (1 << 52) | (bits_x & ((1 << 52) - 1))
        expected_significand_y = 1 << 52
        self.assertEqual(self._evaluate(exponent_x), 2)
        self.assertEqual(self._evaluate(exponent_y), 1)
        self.assertEqual(self._evaluate(significand_x), expected_significand_x)
        self.assertEqual(self._evaluate(significand_y), expected_significand_y)

        exponent_diff = exponent_x - exponent_y
        remainder = _fp_shift_left_bounded(
            claripy.ZeroExt(75, significand_x), exponent_diff, 63
        ) % claripy.ZeroExt(75, significand_y)
        expected_remainder = (
            expected_significand_x << 1
        ) % expected_significand_y
        self.assertEqual(self._evaluate(exponent_diff), 1)
        self.assertEqual(self._evaluate(remainder), expected_remainder)

        encoded = _encode_fp_remainder(
            sign_x,
            remainder,
            exponent_y - claripy.BVV(52, 16),
        )
        self.assertEqual(
            self._evaluate(encoded.raw_to_bv()),
            self._double_bits(math.fmod(5.3, 2.0)),
        )

    def test_prem_uses_truncating_quotient_for_positive_and_negative_inputs(self):
        for dividend in (5.3, -5.3):
            with self.subTest(dividend=dividend):
                result = self._value("Iop_PRemF64", dividend, 2.0)
                self.assertEqual(
                    self._evaluate(result.raw_to_bv()),
                    self._double_bits(math.fmod(dividend, 2.0)),
                )

    def test_prem_keeps_dividend_sign_on_exact_zero(self):
        result = self._value("Iop_PRemF64", -6.0, 3.0)
        self.assertEqual(self._evaluate(result.raw_to_bv()), 1 << 63)

    def test_prem_emits_partial_chunk_and_c2_for_large_exponent_gap(self):
        result = self._value("Iop_PRemF64", 2.0**100, 3.0)
        self.assertEqual(self._evaluate(result.raw_to_bv()), self._double_bits(2.0**40))
        flags = self._value("Iop_PRemC3210F64", 2.0**100, 3.0)
        self.assertEqual(self._evaluate(flags), 1 << 10)

    def test_prem_status_reports_low_signed_quotient_bits(self):
        flags = self._value("Iop_PRemC3210F64", -5.3, 2.0)
        self.assertEqual(self._evaluate(flags), (1 << 8) | (1 << 14))


if __name__ == "__main__":
    unittest.main()
