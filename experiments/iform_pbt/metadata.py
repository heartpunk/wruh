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
print(json.dumps({"fallthrough": instruction.flow_control == iced.FlowControl.NEXT,
                  "defined_flags": defined_mask}))
