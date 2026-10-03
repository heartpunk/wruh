"""Explicit CLE image loading and separate relocated initial-memory data."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from typing import Any
from elftools.elf.elffile import ELFFile
from elftools.elf.relocation import RelocationSection
from cle.backends.elf.relocation import ALL_RELOCATIONS
import angr
from cle.backends.relocation import Relocation
from cle.backends.elf.relocation.generic import (
    RelocTruncate32Mixin, GenericCopyReloc, GenericIRelativeReloc,
    GenericTLSOffsetReloc, GenericTLSModIdReloc, GenericTLSDescriptorReloc,
)


def relocation_write_size(reloc: Any) -> int:
    """Match CLE's implemented write, rather than assume the machine word."""
    method = type(reloc).relocate
    if method is RelocTruncate32Mixin.relocate:
        return 4
    if method is GenericCopyReloc.relocate:
        destination = getattr(reloc.symbol, 'size', None)
        source = getattr(reloc.resolvedby, 'size', None)
        if source and destination != source:
            raise ValueError('COPY relocation source/destination size mismatch')
        size = source or destination
        if type(size) is not int or size <= 0:
            raise ValueError('COPY relocation has no known positive extent')
        return size
    if method is GenericTLSDescriptorReloc.relocate:
        return 2 * reloc.owner.arch.bytes
    if method in (Relocation.relocate, GenericTLSOffsetReloc.relocate,
                  GenericTLSModIdReloc.relocate, GenericIRelativeReloc.relocate):
        return reloc.owner.arch.bytes
    raise ValueError(f'unsupported relocation write extent: {type(reloc).__name__}')


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
    hook_candidates = {project.entry}
    for obj in project.loader.all_objects:
        hook_candidates.update(symbol.rebased_addr for symbol in obj.symbols)
        hook_candidates.update(getattr(obj, "plt", {}).values())
    for address in hook_candidates:
        if project.is_hooked(address):
            project.unhook(address)
    if project.is_hooked(project.entry):
        raise ValueError('entry unexpectedly hooked')
    return project


def skipped_elf_relocations(obj: Any) -> list[dict[str, Any]]:
    """CLE discards unimplemented ELF relocation entries; retain them explicitly."""
    table = ALL_RELOCATIONS.get(obj.arch.name)
    if table is None:
        raise ValueError(f"unsupported ELF relocation architecture: {obj.arch.name}")
    result = []
    with open(obj.binary, 'rb') as stream:
        elf = ELFFile(stream)
        for section in elf.iter_sections():
            if not isinstance(section, RelocationSection):
                continue
            for reloc in section.iter_relocations():
                kind = reloc['r_info_type']
                if kind == 0 or kind in table:
                    continue
                if obj.arch.name != 'AMD64' or kind != 36:
                    raise ValueError(f"unsupported skipped ELF relocation {kind} in {obj.binary}")
                result.append({'address': obj.mapped_base + reloc['r_offset'] - obj.linked_base,
                    'linked_address': reloc['r_offset'], 'elf_type': kind,
                    'size': 16, 'name': 'R_X86_64_TLSDESC',
                    'section': section.name, 'symbol_index': reloc['r_info_sym'],
                    'resolved': False, 'reason': 'unsupported-tls-descriptor'})
    return result


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
        skipped = skipped_elf_relocations(obj)
        undefined_bytes = [{key: record[key] for key in ("address", "size", "reason")} for record in skipped]
        for reloc in obj.relocs:
            symbol = getattr(reloc, 'symbol', None)
            resolved = getattr(reloc, 'resolvedby', None)
            resolved_path = getattr(getattr(resolved, 'owner', None), 'binary', None)
            real_target = bool(resolved_path and Path(resolved_path).is_file())
            pending_resolver = isinstance(reloc, GenericIRelativeReloc)
            if not reloc.resolved or (resolved is not None and not real_target) or pending_resolver:
                undefined_bytes.append({'address': reloc.rebased_addr,
                    'size': relocation_write_size(reloc), 'reason': 'pending-resolver' if pending_resolver else 'unresolved-relocation'})
            relocations.append({'address': reloc.rebased_addr,
                'symbol': symbol.name if symbol else None,
                'resolved': bool(reloc.resolved and (resolved is None or real_target) and not pending_resolver),
                'target': resolved.rebased_addr if resolved else None})
        objects.append({'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'mapped_base': obj.mapped_base, 'linked_base': obj.linked_base,
            'segments': segments, 'relocations': relocations,
            'undefined_bytes': undefined_bytes, 'skipped_relocations': skipped})
    return {'schema': 'wruh-loaded-image-v1', 'objects': objects,
        'initialization_only': True, 'unresolved_relocations_are_open': True,
        'undefined_bytes_override_segment_bytes': True}
