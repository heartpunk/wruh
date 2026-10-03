"""Explicit CLE image loading and separate relocated initial-memory data."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from typing import Any
import angr


def load_object_set(artifact: Path, specification: Path | None = None) -> angr.Project:
    """No dependency searching or SimProcedure substitution; exact object set."""
    objects = json.loads(specification.read_text()) if specification else []
    paths: list[str] = []
    options: dict[str, dict[str, Any]] = {}
    for record in objects:
        path = Path(record['path']).resolve()
        if hashlib.sha256(path.read_bytes()).hexdigest() != record['sha256']:
            raise ValueError(f"object hash mismatch: {path}")
        paths.append(str(path))
        options[str(path)] = {'base_addr': record['base_addr']}
    project = angr.Project(str(artifact), auto_load_libs=False,
        use_sim_procedures=False, load_options={'force_load_libs': paths, 'lib_opts': options})
    actual = {str(Path(obj.binary).resolve()) for obj in project.loader.all_objects
              if getattr(obj, 'binary', None) and Path(obj.binary).is_file()}
    expected = {str(artifact.resolve()), *paths}
    if actual != expected:
        raise ValueError(f"loaded object set differs: expected={expected}, actual={actual}")
    if project.is_hooked(project.entry):
        raise ValueError('entry unexpectedly hooked')
    return project


def loaded_image_data(project: angr.Project) -> dict[str, Any]:
    """Snapshot is an initialization artifact, never instruction semantics."""
    objects = []
    for obj in project.loader.all_objects:
        path = Path(obj.binary) if getattr(obj, 'binary', None) else None
        if path is None or not path.is_file():
            continue
        segments = []
        for segment in obj.segments:
            size = segment.memsize
            segments.append({'address': segment.min_addr, 'size': size,
                'readable': bool(segment.is_readable), 'writable': bool(segment.is_writable),
                'executable': bool(segment.is_executable),
                'bytes': project.loader.memory.load(segment.min_addr, size).hex()})
        relocations = []
        undefined_bytes = []
        for reloc in obj.relocs:
            symbol = getattr(reloc, 'symbol', None)
            resolved = getattr(reloc, 'resolvedby', None)
            resolved_path = getattr(getattr(resolved, 'owner', None), 'binary', None)
            real_target = bool(resolved_path and Path(resolved_path).is_file())
            if not reloc.resolved or (resolved is not None and not real_target):
                undefined_bytes.append({'address': reloc.rebased_addr,
                    'size': project.arch.bytes, 'reason': 'unresolved-relocation'})
            relocations.append({'address': reloc.rebased_addr,
                'symbol': symbol.name if symbol else None,
                'resolved': bool(reloc.resolved and (resolved is None or real_target)),
                'target': resolved.rebased_addr if resolved else None})
        objects.append({'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'mapped_base': obj.mapped_base, 'linked_base': obj.linked_base,
            'segments': segments, 'relocations': relocations,
            'undefined_bytes': undefined_bytes})
    return {'schema': 'wruh-loaded-image-v1', 'objects': objects,
        'initialization_only': True, 'unresolved_relocations_are_open': True,
        'undefined_bytes_override_segment_bytes': True}
