"""Restore the unsigned AMD64 DIV overflow exit omitted by the provider.

Intel SDM, DIV: quotient > 2**operand_bits - 1 raises #DE before writeback.
For an unsigned double-width dividend this is exactly high_half >= divisor.
The provider's existing zero-divisor exit and arithmetic remain unchanged.
"""

from copy import deepcopy

import capstone
import pyvex


def unsigned_divide_irsb(block):
    """Return a private guarded IRSB for DIV, or None for other instructions.

    Read operands from the lifted operation, so register aliases, effective
    addresses and memory reads retain their provider semantics. Fail visibly
    if a future provider changes this expected lowering. Never mutate the
    project's cached block or patch the process-wide engine.
    """
    instruction = block.capstone.insns[0]
    if instruction.id != capstone.x86.X86_INS_DIV:
        return None
    if len(instruction.operands) != 1:
        raise ValueError("unexpected AMD64 DIV operand count")
    bits = instruction.operands[0].size * 8
    if bits not in (8, 16, 32, 64):
        raise ValueError("unexpected AMD64 DIV operand width")
    irsb = deepcopy(block.vex)
    operation = "Iop_DivModU128to64" if bits == 64 else "Iop_DivModU64to32"
    divisions = [statement for statement in irsb.statements
                 if isinstance(statement, pyvex.stmt.WrTmp)
                 and isinstance(statement.data, pyvex.expr.Binop)
                 and statement.data.op == operation]
    if len(divisions) != 1:
        raise ValueError("unexpected AMD64 DIV lowering: expected one unsigned DivMod")
    division = divisions[0]
    dividend, divisor = division.data.args
    added = []

    def temporary(ty, expression):
        index = irsb.tyenv.add(ty)
        added.append(pyvex.stmt.WrTmp(index, expression))
        return pyvex.expr.RdTmp(index)

    if bits == 64:
        high = temporary("Ity_I64", pyvex.expr.Unop("Iop_128HIto64", [dividend]))
        compare = "Iop_CmpLT64U"
    else:
        shifted = temporary("Ity_I64", pyvex.expr.Binop(
            "Iop_Shr64", [dividend, pyvex.expr.Const(pyvex.const.U8(bits))]))
        high = temporary("Ity_I32", pyvex.expr.Unop("Iop_64to32", [shifted]))
        compare = "Iop_CmpLT32U"
    # This orientation exports ULT/UGE, both admitted by the pinned typed
    # exporter. Negating divisor <= high would instead produce unsupported UGT.
    fits = temporary("Ity_I1", pyvex.expr.Binop(compare, [high, divisor]))
    overflow = temporary("Ity_I1", pyvex.expr.Unop("Iop_Not1", [fits]))
    added.append(pyvex.stmt.Exit(
        overflow, pyvex.const.U64(block.addr), "Ijk_SigFPE_IntDiv", irsb.offsIP))
    index = irsb.statements.index(division)
    irsb.statements[index:index] = added
    return irsb
