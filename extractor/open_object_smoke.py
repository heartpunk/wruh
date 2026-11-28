"""Load or compile trusted fixture as data, then load/inventory/extract; never execute it."""
from extractor.runtime_trace import start_runtime_trace

start_runtime_trace()
from extractor.native_runtime import preload_libstdcxx

preload_libstdcxx()
import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from extractor.backend import Session
from extractor.elf_fixture import elf_fixture
from extractor.fresh import extract_linear, linear_site_records


def main(argv=None):
    parser=argparse.ArgumentParser(); parser.add_argument('--entry',type=Path,required=True)
    parser.add_argument('--library',type=Path,required=True); parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--fixture-directory', type=Path)
    args=parser.parse_args(argv)
    with tempfile.TemporaryDirectory() as temp:
        directory=Path(temp); library=directory/'libfixture.so'; entry=directory/'fixture.elf'
        if args.fixture_directory:
            metadata = json.loads((args.fixture_directory / 'manifest.json').read_text())
            for name, source in [('entry.c', args.entry), ('library.c', args.library)]:
                if hashlib.sha256(source.read_bytes()).hexdigest() != metadata['sources'][name]:
                    raise ValueError(f'fixture source hash mismatch: {name}')
            for name, destination in [('fixture.elf', entry), ('libfixture.so', library)]:
                data = (args.fixture_directory / name).read_bytes()
                if hashlib.sha256(data).hexdigest() != metadata['outputs'][name]:
                    raise ValueError(f'fixture output hash mismatch: {name}')
                # ELF64 little-endian AMD64; never execute these data files.
                if data[:6] != b'\x7fELF\x02\x01' or int.from_bytes(data[18:20], 'little') != 62:
                    raise ValueError(f'fixture is not AMD64 ELF64: {name}')
                destination.write_bytes(data)
            commands = metadata['generation_commands']
        else:
            compiler = shutil.which('clang')
            if compiler is None:
                raise RuntimeError('declared clang runtime absent')
            commands=[[compiler,'-O2','-fno-stack-protector','-fno-builtin','-fPIC','-shared','-nostdlib',str(args.library),'-o',str(library)],
                [compiler,'-O2','-fno-stack-protector','-fno-builtin','-nostdlib','-no-pie','-Wl,-e,direct_root',str(args.entry),'-L'+temp,'-lfixture','-o',str(entry)]]
            for command in commands:
                subprocess.run(command,check=True)
        specification=directory/'objects.json'; specification.write_text(json.dumps([
            {'path':str(library),'base_addr':0x900000,'sha256':hashlib.sha256(library.read_bytes()).hexdigest()}]))
        session=Session.load(entry,specification)
        image=session.image.loaded_image
        assert len(image['objects'])==2
        decoded = session.inventory([])
        records = linear_site_records(decoded, chunk_size=32, seed=17)
        extraction = extract_linear(session, records)
        library_hash = hashlib.sha256(library.read_bytes()).hexdigest()
        entry_hash = hashlib.sha256(entry.read_bytes()).hexdigest()
        assert {item.origin.image_sha256 for item in extraction.occurrences} == {entry_hash, library_hash}
        entry_object = next(obj for obj in image["objects"] if obj["sha256"] == entry_hash)
        indirect = next(symbol for symbol in entry_object["function_symbols"]
                        if "indirect_root" in symbol["names"])
        address = entry_object["mapped_base"] + indirect["offset"]
        indirect_edges = [edge for edge in extraction.local_edges
                          if address <= edge.source < address + indirect["size"]]
        assert any(edge.summary.target.kind == 'symbolic' for edge in indirect_edges)
        relocation_file = directory / "relocations.so"
        elf_fixture(relocation_file, [(0, 2, 1, 0), (8, 1, 1, 0), (24, 5, 1, 0),
                                      (48, 36, 1, 0)], import_size=24)
        relocation_obj = Session.load(relocation_file).image.loaded_image["objects"][0]
        base = relocation_obj["mapped_base"]
        masks = sorted((r["address"] - base, r["size"]) for r in relocation_obj["undefined_bytes"])
        assert masks == [(0x300, 4), (0x308, 8), (0x318, 24), (0x330, 16)]
        skipped, = relocation_obj["skipped_relocations"]
        assert skipped["elf_type"] == 36 and skipped["size"] == 16
        elf_fixture(relocation_file, [(0, 999, 1, 0)])
        try:
            Session.load(relocation_file)
        except ValueError as error:
            assert "unsupported skipped ELF relocation 999" in str(error)
        else:
            raise AssertionError("unknown skipped ELF relocation accepted")
        result={'skipped_relocation_controls':'raw TLSDESC16 retained / unknown fails explicitly',
            'relocation_controls':{'pc32_bytes':4,'word_bytes':8,'copy_bytes':24,'neighbor_sentinels':'retained','unknown_extent':'explicit rejection'},
            'commands':commands,'source_hashes':{str(source):hashlib.sha256(source.read_bytes()).hexdigest() for source in (args.entry,args.library)},
            'objects':[{key:obj[key] for key in ('sha256','mapped_base','linked_base','relocations','undefined_bytes')} for obj in image['objects']],
            'decoded':len(decoded.decoded), 'unresolved':len(decoded.unresolved), 'unexamined':len(decoded.unexamined),
            'local_edges':len(extraction.local_edges), 'indirect_target':'symbolic', 'native_execution':False}
        args.output.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')

if __name__=='__main__': main()
