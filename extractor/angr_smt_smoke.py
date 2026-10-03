"""Public Angr SMT boundary checks; no candidate binary execution."""
from extractor.amd64_state import claripy_to_z3, LTS_EXTRACTION_CONTEXT
from extractor.runtime import claripy as c
import z3

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
for name, term, expected in cases:
    actual = claripy_to_z3(term)
    assert actual.sort() == expected.sort(), name
    assert claripy_to_z3(term) is actual, name
    solver = z3.Solver(ctx=LTS_EXTRACTION_CONTEXT)
    solver.add(actual != expected)
    assert solver.check() == z3.unsat, name
    print(name, 'UNSAT', flush=True)
