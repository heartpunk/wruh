from types import SimpleNamespace
import unittest

from extractor.instruction_inventory import Interval, Span, inventory, shuffled_chunks


class Decoder:
    def disasm(self, data, address, count):
        assert count == 1
        if data[0] == 0xff or (data[0] == 0xaa and len(data) < 2):
            return iter(())
        size = 2 if data[0] == 0xaa else 1
        return iter((SimpleNamespace(address=address, size=size, bytes=data[:size],
                                     mnemonic="op", op_str=""),))


class InstructionInventoryTest(unittest.TestCase):
    def test_decode_precedes_chunking_and_exclusions_bound_decode(self):
        result = inventory([Span(0x1000, b'\xaa\x01\xff\xaa\x02\x03')],
                           [Interval(0x1004, 0x1005)], Decoder())
        self.assertEqual([(item.address, item.data) for item in result.decoded],
                         [(0x1000, b'\xaa\x01'), (0x1005, b'\x03')])
        self.assertEqual(result.unresolved,
                         (Interval(0x1002, 0x1003),))
        self.assertEqual(result.unexamined, (Interval(0x1003, 0x1004),
                                             Interval(0x1004, 0x1005)))
        self.assertEqual(sorted(item.address for chunk in shuffled_chunks(result, 1, 42)
                                for item in chunk), [0x1000, 0x1005])

    def test_rejects_overlapping_spans(self):
        with self.assertRaisesRegex(ValueError, "overlap"):
            inventory([Span(0, b'12'), Span(1, b'3')], [], Decoder())
