"""Compile trusted fixture as data, then load/inventory/extract; never execute it."""
from extractor.runtime_trace import start_runtime_trace
start_runtime_trace()
from extractor.native_runtime import preload_libstdcxx
preload_libstdcxx()
import argparse, hashlib, json, shutil, subprocess, tempfile
from pathlib import Path
from extractor.loaded_image import load_object_set, loaded_image_data, relocation_write_size
from cle.backends.elf.relocation.amd64 import R_X86_64_PC32, R_X86_64_64, R_X86_64_COPY
from cle.backends.relocation import Relocation
from types import SimpleNamespace
from extractor.binary_inventory import inventory_project, exact_symbol_inventory_policy, PinnedBinary
from extractor.binary_cfg import build_static_cfg
from extractor.fresh import extract_fresh_function


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--entry',type=Path,required=True)
    parser.add_argument('--library',type=Path,required=True); parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(); compiler=shutil.which('clang')
    if compiler is None: raise RuntimeError('declared clang runtime absent')
    with tempfile.TemporaryDirectory() as temp:
        directory=Path(temp); library=directory/'libfixture.so'; entry=directory/'fixture.elf'
        commands=[[compiler,'-O2','-fno-stack-protector','-fno-builtin','-fPIC','-shared','-nostdlib',str(args.library),'-o',str(library)],
            [compiler,'-O2','-fno-stack-protector','-fno-builtin','-nostdlib','-no-pie','-Wl,-e,direct_root',str(args.entry),'-L'+temp,'-lfixture','-o',str(entry)]]
        for command in commands: subprocess.run(command,check=True)
        specification=directory/'objects.json'; specification.write_text(json.dumps([
            {'path':str(library),'base_addr':0x900000,'sha256':hashlib.sha256(library.read_bytes()).hexdigest()}]))
        project=load_object_set(entry,specification)
        image=loaded_image_data(project)
        assert len(image['objects'])==2
        roots=('direct_root','indirect_root','tail_root','child')
        manifest=inventory_project(project,entry,exact_symbol_inventory_policy(roots,open_transfers=True))
        pinned=PinnedBinary(entry,manifest,project); cfg=build_static_cfg(pinned)
        functions=[extract_fresh_function(pinned,cfg,name) for name in cfg["roots"]]
        assert any(name.startswith("plt:child:") for name in cfg["roots"])
        library_hash=hashlib.sha256(library.read_bytes()).hexdigest()
        child=next(f for f in functions if f.function_id=='child')
        assert all(item.origin.image_sha256==library_hash for item in child.occurrences)
        assert any(call['target'] is None for call in cfg['roots']['indirect_root']['calls'])
        assert all(not project.is_hooked(root['address']) for root in manifest['roots'].values())
        # Actual CLE relocation classes: unknown-mask extent follows their writes.
        memory_bytes=bytes(range(64)); fixture_path=directory/'relocation.bin'; fixture_path.write_bytes(memory_bytes)
        segment=SimpleNamespace(min_addr=0x1000,memsize=64,is_readable=True,is_writable=True,is_executable=False)
        owner=SimpleNamespace(binary=str(fixture_path),mapped_base=0x1000,linked_base=0,arch=SimpleNamespace(bytes=8),segments=[segment],imports={})
        symbol=SimpleNamespace(name='unknown',size=24,is_import=False)
        owner.relocs=[R_X86_64_PC32(owner,symbol,0,addend=0),R_X86_64_64(owner,symbol,8,addend=0),R_X86_64_COPY(owner,symbol,24,addend=0)]
        fake=SimpleNamespace(loader=SimpleNamespace(all_objects=[owner],memory=SimpleNamespace(load=lambda address,size: memory_bytes[address-0x1000:address-0x1000+size])))
        masks=loaded_image_data(fake)['objects'][0]['undefined_bytes']
        assert [(item['address'],item['size']) for item in masks]==[(0x1000,4),(0x1008,8),(0x1018,24)]
        masked={address for item in masks for address in range(item['address'],item['address']+item['size'])}
        assert 0x1004 not in masked and 0x1007 not in masked and 0x1030 not in masked
        assert all(address in masked for address in range(0x1018,0x1030))
        class UnknownRelocation(Relocation):
            def relocate(self): return True
        try: relocation_write_size(UnknownRelocation(owner,symbol,0))
        except ValueError: pass
        else: raise AssertionError('unknown write extent accepted')
        result={'relocation_controls':{'pc32_bytes':4,'word_bytes':8,'copy_bytes':24,'neighbor_sentinels':'retained','unknown_extent':'explicit rejection'},'commands':commands,'source_hashes':{str(source):hashlib.sha256(source.read_bytes()).hexdigest() for source in (args.entry,args.library)},
            'objects':[{key:obj[key] for key in ('sha256','mapped_base','linked_base','relocations','undefined_bytes')} for obj in image['objects']],
            'roots':manifest['roots'],'local_edges':{f.function_id:len(f.local_edges) for f in functions},
            'indirect_calls':cfg['roots']['indirect_root']['calls'], 'native_execution':False}
        args.output.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')

if __name__=='__main__': main()
