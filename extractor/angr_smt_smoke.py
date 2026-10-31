"""Public Angr SMT boundary checks; no candidate binary execution."""
from extractor.amd64_state import claripy_to_z3, LTS_EXTRACTION_CONTEXT
from extractor.runtime import claripy as c
import z3

def check():
    x, y, b = c.BVS('x', 64, explicit_name=True), c.BVS('y', 64, explicit_name=True), c.BoolS('b', explicit_name=True)
    xz, yz, bz = z3.BitVec('x', 64, ctx=LTS_EXTRACTION_CONTEXT), z3.BitVec('y', 64, ctx=LTS_EXTRACTION_CONTEXT), z3.Bool('b', ctx=LTS_EXTRACTION_CONTEXT)
    cases = [
        ('true', c.BoolV(True), z3.BoolVal(True, ctx=LTS_EXTRACTION_CONTEXT)),
        ('false', c.BoolV(False), z3.BoolVal(False, ctx=LTS_EXTRACTION_CONTEXT)),
        ('bool_symbol', b, bz),
        ('bv_symbol', x, xz),
        ('add', x + y, xz + yz),
        ('udiv', c.UDiv(x, y), z3.UDiv(xz, yz)),
        ('urem', c.UMod(x, y), z3.URem(xz, yz)),
        ('shift', c.LShR(x, y), z3.LShR(xz, yz)),
        ('extract', c.Extract(7, 0, x), z3.Extract(7, 0, xz)),
        ('extend', c.ZeroExt(8, x), z3.ZeroExt(8, xz)),
        ('ite', c.If(b, x, y), z3.If(bz, xz, yz)),
        ('relation', c.ULT(x, y), z3.ULT(xz, yz)),
    ]
    # Exercise every corrected exporter conversion at both IEEE storage widths.
    for width, ebits, sbits in [(32, 8, 24), (64, 11, 53)]:
        sort = c.FSORT_FLOAT if width == 32 else c.FSORT_DOUBLE
        zsort = z3.FPSort(ebits, sbits, ctx=LTS_EXTRACTION_CONTEXT)
        bits = c.BVS(f"fp_bits_{width}", width, explicit_name=True)
        zbits = z3.BitVec(f"fp_bits_{width}", width, ctx=LTS_EXTRACTION_CONTEXT)
        other_width = 64 if width == 32 else 32
        other = c.FPS(f"fp_source_{width}", c.FSORT_FLOAT if other_width == 32 else c.FSORT_DOUBLE, explicit_name=True)
        zother = z3.FP(f"fp_source_{width}", z3.FPSort(11, 53, ctx=LTS_EXTRACTION_CONTEXT) if other_width == 64 else z3.FPSort(8, 24, ctx=LTS_EXTRACTION_CONTEXT))
        rm = c.fp.RM.RM_NearestTiesEven
        zrm = z3.RNE(ctx=LTS_EXTRACTION_CONTEXT)
        cases.extend([
            (f"fp_reinterpret_{width}", c.fpAbs(bits.raw_to_fp()), z3.fpAbs(z3.fpBVToFP(zbits, zsort, ctx=LTS_EXTRACTION_CONTEXT), ctx=LTS_EXTRACTION_CONTEXT)),
            (f"fp_signed_{width}", bits.val_to_fp(sort, signed=True, rm=rm), z3.fpSignedToFP(zrm, zbits, zsort, ctx=LTS_EXTRACTION_CONTEXT)),
            (f"fp_unsigned_{width}", bits.val_to_fp(sort, signed=False, rm=rm), z3.fpUnsignedToFP(zrm, zbits, zsort, ctx=LTS_EXTRACTION_CONTEXT)),
            (f"fp_cast_{width}", other.to_fp(sort, rm), z3.fpToFP(zrm, zother, zsort, ctx=LTS_EXTRACTION_CONTEXT)),
        ])
    # Machine-facing conversion carries FP through bit-backed storage.
    for name, term, expected in cases:
        if z3.is_fp(expected):
            term, expected = term.raw_to_bv(), z3.fpToIEEEBV(expected, ctx=LTS_EXTRACTION_CONTEXT)
        actual = claripy_to_z3(term)
        assert actual.sort() == expected.sort(), name
        assert claripy_to_z3(term) is actual, name
        solver = z3.Solver(ctx=LTS_EXTRACTION_CONTEXT)
        solver.add(actual != expected)
        assert solver.check() == z3.unsat, name
        print(name, 'UNSAT', flush=True)


if __name__ == "__main__":
    check()
