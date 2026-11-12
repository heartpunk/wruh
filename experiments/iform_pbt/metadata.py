#!/usr/bin/env python3
"""Decode native-observation constraints using the catalogue's iced-x86."""
import json
import sys

import iced_x86 as iced

data = bytes.fromhex(sys.argv[1])
decoder = iced.Decoder(64, data, ip=0x400170)
instruction = decoder.decode()
if instruction.is_invalid or instruction.len != len(data):
    raise ValueError("bytes do not decode as exactly one instruction")

flags = {"CF": 0, "PF": 2, "AF": 4, "ZF": 6, "SF": 7, "OF": 11}
undefined = instruction.rflags_undefined
defined_mask = sum(1 << bit for name, bit in flags.items()
                   if not undefined & getattr(iced.RflagsBits, name))
memory = iced.InstructionInfoFactory().info(instruction).used_memory()
registers = [iced.Register.RAX, iced.Register.RCX, iced.Register.RDX,
             iced.Register.RBX, iced.Register.RSP, iced.Register.RBP,
             iced.Register.RSI, iced.Register.RDI, iced.Register.R8,
             iced.Register.R9, iced.Register.R10, iced.Register.R11,
             iced.Register.R12, iced.Register.R13, iced.Register.R14,
             iced.Register.R15]
address = None
supported = not memory
if len(memory) == 1 and not (instruction.has_rep_prefix or instruction.has_repne_prefix):
    access = memory[0]
    width = iced.MemorySizeExt.size(access.memory_size)
    displacement = access.displacement
    signed_displacement = displacement if displacement < 2**63 else displacement - 2**64
    if (access.base == iced.Register.RSP and access.index == iced.Register.NONE
            and access.segment == iced.Register.SS and 0 < width <= 1024
            and 0 <= 1008 + signed_displacement <= 1024 - width):
        supported = True
    elif (access.base in registers and access.base != iced.Register.RSP
            and access.index == iced.Register.NONE
            and access.segment in (iced.Register.DS, iced.Register.SS)
            and 0 < width <= 1024):
        supported = True
        address = {"base": registers.index(access.base),
                   "displacement": access.displacement, "width": width}
print(json.dumps({"fallthrough": instruction.flow_control == iced.FlowControl.NEXT,
                  "defined_flags": defined_mask, "address_supported": supported,
                  "address": address}))
