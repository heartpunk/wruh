from types import SimpleNamespace
from pathlib import Path
import tempfile
import unittest

from extractor.instruction_inventory import Interval, Span, inventory, inventory_project, shuffled_chunks


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

    def test_project_scans_executable_segments_without_symbols(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "image"
            path.write_bytes(b"image")
            segment = SimpleNamespace(is_executable=True, memsize=3, min_addr=0x2000)
            other = SimpleNamespace(is_executable=False, memsize=1, min_addr=0x3000)
            image = SimpleNamespace(binary=str(path), segments=[segment, other])
            memory = SimpleNamespace(load=lambda address, size: b"\x01\x02\x03")
            project = SimpleNamespace(arch=SimpleNamespace(name="AMD64", bits=64, capstone=Decoder()),
                                      loader=SimpleNamespace(all_objects=[image], memory=memory))
            result = inventory_project(project, [Interval(0x2001, 0x2002)])
            self.assertEqual([item.address for item in result.decoded], [0x2000, 0x2002])
            self.assertEqual(result.unexamined, (Interval(0x2001, 0x2002),))

    def test_real_x86_instruction_boundaries_are_independent_of_chunks(self):
        try:
            import capstone
        except ImportError:
            self.skipTest("capstone is not available")
        decoder = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
        result = inventory([Span(0x1000, bytes.fromhex("b80100000090c3"))], [], decoder)
        self.assertEqual([item.address for item in result.decoded], [0x1000, 0x1005, 0x1006])
        self.assertEqual(result.unresolved, ())
        self.assertEqual(result.unexamined, ())
        expected = {(item.address, item.data) for item in result.decoded}
        for seed in range(10):
            actual = {(item.address, item.data) for chunk in shuffled_chunks(result, 1, seed) for item in chunk}
            self.assertEqual(actual, expected)
