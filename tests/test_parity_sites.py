import unittest
from extractor.parity_sites import match_sites


def model(sites, edges, base=0, digest='a' * 64):
    return {'occurrences': [{'origin': {'canonical_address': base + a,
                            'image_sha256': digest, 'mapped_base': base,
                            'object_offset': a, 'decode_mode': 'long64'}} for a in sites],
            'local_edges': [{'source': base + a, 'edge_id': {'outcome_id': outcome,
                            'static_occurrence_id': identity}} for a, outcome, identity in edges]}


class SiteParityTests(unittest.TestCase):
    def test_compares_shared_sites_without_conflating_inventory_changes(self):
        old = model([1, 2], [(1, 0, 7), (2, 0, 8)])
        new = model([1, 3], [(1, 0, 900), (1, 1, 900), (3, 0, 901)])
        result = match_sites(old, new)
        self.assertEqual(result['only_baseline_sites'], [(('a' * 64, 2, 'long64'), 0)])
        self.assertEqual(result['only_candidate_sites'], [(('a' * 64, 3, 'long64'), 0)])
        self.assertEqual(result['only_baseline_edges'], [])
        self.assertEqual(result['only_candidate_edges'], [((('a' * 64, 1, 'long64'), 0), 1)])
        self.assertEqual([item[0] for item in result['shared_edges']], [((('a' * 64, 1, 'long64'), 0), 0)])

    def test_rejects_ambiguous_edge_identity(self):
        duplicate = model([1], [(1, 0, 0), (1, 0, 1)])
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            match_sites(duplicate, duplicate)

    def test_repeated_owners_do_not_duplicate_the_same_edge(self):
        from extractor.parity_sites import combine_models
        instruction = {'origin': {'canonical_address': 1, 'image_sha256': 'a',
                       'instruction_bytes': '90', 'architecture': 'AMD64', 'decode_mode': 'long64'}}
        edge = {'source': 1, 'edge_id': {'outcome_id': 0, 'static_occurrence_id': 1}, 'summary': {}}
        function = {'declarations': [], 'occurrences': [instruction], 'local_edges': [edge]}
        result = combine_models([function, function])
        self.assertEqual(len(result['occurrences']), 1)
        self.assertEqual(len(result['local_edges']), 1)

    def test_remapped_sites_match_by_backing_object(self):
        old = model([1], [(1, 0, 5)], base=0x1000)
        new = model([1], [(1, 0, 99)], base=0x9000)
        result = match_sites(old, new)
        self.assertEqual(len(result['shared_edges']), 1)
        self.assertEqual(result['only_baseline_sites'], [])
        distinct = model([1], [(1, 0, 99)], base=0x9000, digest='b' * 64)
        self.assertEqual(match_sites(old, distinct)['shared_edges'], [])

    def test_baseline_origin_identity_uses_backing_object_mapping(self):
        from extractor.parity_sites import attach_mapping_identity
        item = {'origin': {'canonical_address': 0x1020, 'image_sha256': 'a' * 64}}
        bundle = {'functions': [{'occurrences': [item]}], 'loaded_image': {'objects': [
            {'sha256': 'a' * 64, 'mapped_base': 0x1000,
             'segments': [{'address': 0x1000, 'size': 0x100}]}]}}
        attach_mapping_identity(bundle)
        self.assertEqual(item['origin']['object_offset'], 0x20)
        self.assertEqual(item['origin']['mapped_base'], 0x1000)

    def test_same_object_mappings_remain_separate_instances(self):
        first = model([1], [(1, 0, 1)], base=0x1000)
        second = model([1], [(1, 0, 2)], base=0x3000)
        both = {'occurrences': first['occurrences'] + second['occurrences'],
                'local_edges': first['local_edges'] + second['local_edges']}
        result = match_sites(both, both)
        self.assertEqual(len(result['shared_edges']), 2)
        self.assertNotEqual(result['shared_edges'][0][0], result['shared_edges'][1][0])
