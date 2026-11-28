import unittest
from extractor.parity_sites import match_sites


def model(sites, edges):
    return {'occurrences': [{'origin': {'canonical_address': a}} for a in sites],
            'local_edges': [{'source': a, 'edge_id': {'outcome_id': outcome,
                            'static_occurrence_id': identity}} for a, outcome, identity in edges]}


class SiteParityTests(unittest.TestCase):
    def test_compares_shared_sites_without_conflating_inventory_changes(self):
        old = model([1, 2], [(1, 0, 7), (2, 0, 8)])
        new = model([1, 3], [(1, 0, 900), (1, 1, 900), (3, 0, 901)])
        result = match_sites(old, new)
        self.assertEqual(result['only_baseline_sites'], [2])
        self.assertEqual(result['only_candidate_sites'], [3])
        self.assertEqual(result['only_baseline_edges'], [])
        self.assertEqual(result['only_candidate_edges'], [(1, 1)])
        self.assertEqual([item[0] for item in result['shared_edges']], [(1, 0)])

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
