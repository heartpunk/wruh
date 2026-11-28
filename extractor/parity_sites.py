"""Match local edge identities across independent extraction inventories."""
from __future__ import annotations


def match_sites(before, after):
    """Match by object digest, relative offset, mode and mapping instance."""
    def collect(model):
        origins = [item['origin'] for item in model['occurrences']]
        bases = {}
        for origin in origins:
            bases.setdefault(origin['image_sha256'], set()).add(origin['mapped_base'])
        base_indices = {digest: {base: index for index, base in enumerate(sorted(values))}
                        for digest, values in bases.items()}
        address_to_key = {}
        for origin in origins:
            digest, base = origin['image_sha256'], origin['mapped_base']
            key = ((digest, origin['object_offset'], origin['decode_mode']), base_indices[digest][base])
            address = origin['canonical_address']
            if address in address_to_key or key in address_to_key.values():
                raise ValueError(f'ambiguous site identity {key!r}')
            address_to_key[address] = key
        edges = {}
        for edge in model['local_edges']:
            if edge['source'] not in address_to_key:
                raise ValueError('edge source has no instruction evidence')
            key = (address_to_key[edge['source']], edge['edge_id']['outcome_id'])
            if key in edges:
                raise ValueError(f'duplicate edge identity {key!r}')
            edges[key] = edge
        return set(address_to_key.values()), edges
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


def combine_models(functions):
    """Combine repeated site observations, rejecting inconsistent duplicates."""
    if not functions:
        raise ValueError('bundle has no extraction records')
    declarations = functions[0]['declarations']
    occurrences = {}
    edges = {}
    for function in functions:
        if function['declarations'] != declarations:
            raise ValueError('declaration sets differ within bundle')
        for item in function['occurrences']:
            origin = item['origin']
            address = origin['canonical_address']
            previous = occurrences.get(address)
            if previous is not None:
                fields = ('image_sha256', 'instruction_bytes', 'architecture', 'decode_mode')
                if any(previous['origin'][field] != origin[field] for field in fields):
                    raise ValueError(f'inconsistent instruction at {address:#x}')
            else:
                occurrences[address] = item
        for edge in function['local_edges']:
            key = (edge['source'], edge['edge_id']['outcome_id'])
            previous = edges.get(key)
            if previous is not None:
                fields = ('summary', 'jumpkind', 'fault_kind')
                if any(previous.get(field) != edge.get(field) for field in fields):
                    raise ValueError(f'inconsistent duplicate edge {key!r}')
            else:
                edges[key] = edge
    return {'declarations': declarations, 'occurrences': list(occurrences.values()),
            'local_edges': list(edges.values())}


def attach_mapping_identity(bundle):
    """Annotate observations using the explicit loaded-object snapshot."""
    objects = bundle.get('loaded_image', {}).get('objects', [])
    models = [bundle['extraction']] if 'extraction' in bundle else bundle['functions']
    for model in models:
        for occurrence in model['occurrences']:
            origin = occurrence['origin']
            if 'object_offset' in origin and 'mapped_base' in origin:
                continue
            address = origin['canonical_address']
            matches = [obj for obj in objects if obj['sha256'] == origin['image_sha256']
                       and any(segment['address'] <= address < segment['address'] + segment['size']
                               for segment in obj['segments'])]
            if len(matches) != 1:
                raise ValueError(f'cannot resolve one backing object for {address:#x}')
            base = matches[0]['mapped_base']
            origin['mapped_base'] = base
            origin['object_offset'] = address - base
    return bundle
