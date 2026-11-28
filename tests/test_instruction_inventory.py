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
        self.assertEqual(result.unexamined, (Interval(0x1003, 0x1004),))
        self.assertNotIn(Interval(0x1004, 0x1005), result.unexamined)
        self.assertEqual(sorted(item.address for chunk in shuffled_chunks(result, 1, 42)
                                for item in chunk), [0x1000, 0x1005])

    def test_rejects_overlapping_spans(self):
        with self.assertRaisesRegex(ValueError, "overlap"):
            inventory([Span(0, b'12'), Span(1, b'3')], [], Decoder())

    def test_session_scans_executable_segments_without_symbols(self):
        from extractor.backend import Session
        obj = {"sha256": "a" * 64, "mapped_base": 0x2000, "segments": [
            {"address": 0x2000, "size": 3, "bytes": "909090", "executable": True},
            {"address": 0x3000, "size": 1, "bytes": "90", "executable": False},
        ]}
        session = Session(None, SimpleNamespace(loaded_image={"objects": [obj]}))
        result = session.inventory([Interval(0x2001, 0x2002)])
        self.assertEqual([item.address for item in result.decoded], [0x2000, 0x2002])
        self.assertEqual(result.unexamined, ())

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

    def test_site_identity_survives_remapping_and_distinguishes_objects(self):
        def decode(base, digest):
            return inventory([Span(base + 0x20, b"\x90\xc3", digest, base)], [], Decoder())
        first = decode(0x1000, "a" * 64)
        remapped = decode(0x9000, "a" * 64)
        other = decode(0x1000, "b" * 64)
        self.assertEqual([i.site_key for i in first.decoded], [i.site_key for i in remapped.decoded])
        self.assertNotEqual(first.decoded[0].site_key, other.decoded[0].site_key)
        self.assertNotEqual(first.decoded[0].address, remapped.decoded[0].address)
        self.assertEqual([[i.site_key for i in c] for c in shuffled_chunks(first, 1, 12)],
                         [[i.site_key for i in c] for c in shuffled_chunks(remapped, 1, 12)])
