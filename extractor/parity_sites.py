"""Match local edge identities across independent extraction inventories."""
from __future__ import annotations


def match_sites(before, after):
    """Return address and outcome differences separately from shared edges."""
    def collect(model):
        sites = {item['origin']['canonical_address'] for item in model['occurrences']}
        edges = {}
        for edge in model['local_edges']:
            key = (edge['source'], edge['edge_id']['outcome_id'])
            if key in edges:
                raise ValueError(f'duplicate edge identity {key!r}')
            edges[key] = edge
        return sites, edges
    old_sites, old_edges = collect(before)
    new_sites, new_edges = collect(after)
    shared = old_sites & new_sites
    old_keys = {key for key in old_edges if key[0] in shared}
    new_keys = {key for key in new_edges if key[0] in shared}
    return {
        'only_baseline_sites': sorted(old_sites - new_sites),
        'only_candidate_sites': sorted(new_sites - old_sites),
        'only_baseline_edges': sorted(old_keys - new_keys),
        'only_candidate_edges': sorted(new_keys - old_keys),
        'shared_edges': [(key, old_edges[key], new_edges[key]) for key in sorted(old_keys & new_keys)],
    }
