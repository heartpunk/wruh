"""Bounded native differential attempts for every catalogue encoding.

The comparator handles integer and mapped-memory instructions and FXSAVE XMM
state. Unsupported state or outcomes are reported as INCOMPLETE.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import importlib.metadata
import json
import math
import os
import platform
import re
import time
import multiprocessing
from pathlib import Path

from hypothesis import given, settings, strategies as st
from hypothesis.database import DirectoryBasedExampleDatabase
import iced_x86 as ice

from extractor.catalogue_models import prepare_model
from extractor.iform_candidates import CandidateError, CandidateTemplate, inspect_operands, xed_iform_decoder
from extractor.isolated_native import NativeIsolationError, bubblewrap_command, require_bounded_cgroup
from extractor.native_memory_scope import MemoryScopeError
from extractor.native_state_differential import compare_native_state
from extractor.native_step import REGISTERS, capture_step


def _candidate_registers(encoded: bytes, values: dict[str, int],
                         fs_base: int = 0, gs_base: int = 0) -> dict[str, int]:
    """Place simple memory bases in the data page without solving constraints."""
    registers = dict(values)
    ins = ice.Decoder(64, encoded, ip=0x400000).decode()
    names = {value: name.lower() for name, value in vars(ice.Register).items()
             if name.isupper() and isinstance(value, int)}
    for mem in ice.InstructionInfoFactory().info(ins).used_memory():
        base = names.get(ice.RegisterExt.full_register(mem.base))
        index = names.get(ice.RegisterExt.full_register(mem.index))
        bits = 32 if mem.address_size == ice.CodeSize.CODE32 else 64
        mask = (1 << bits) - 1
        if base == 'rsp' or index == 'rsp':
            registers['rsp'] = 0x200800
        if index in registers and index != base:
            registers[index] &= ~mask
        if base in registers and base != 'rsp':
            segment = fs_base if mem.segment == ice.Register.FS else gs_base if mem.segment == ice.Register.GS else 0
            rhs = (0x100800 - mem.displacement - segment) & mask
            factor = 1 + mem.scale if index == base else 1
            divisor = math.gcd(factor, 1 << bits)
            rhs += (-rhs) % divisor  # Adjust within the data page when necessary.
            modulus = (1 << bits) // divisor
            low = ((rhs // divisor) * pow(factor // divisor, -1, modulus)) % modulus
            registers[base] = (registers[base] & ~mask) | low
    return registers


def _register_bindings(encoded: bytes) -> list[dict[str, int]]:
    """Enumerate same-class register bindings; encoder/XED validate each."""
    ins = ice.Decoder(64, encoded, ip=0x400000).decode()
    all_regs = {value for name, value in vars(ice.Register).items()
                if name.isupper() and isinstance(value, int)}
    candidates = [{}]
    for index in range(ins.op_count):
        if ins.op_kind(index) != ice.OpKind.REGISTER:
            continue
        original = getattr(ins, f'op{index}_register')
        base, width = ice.RegisterExt.base(original), ice.RegisterExt.size(original)
        for register in sorted(all_regs):
            if register != original and ice.RegisterExt.base(register) == base and ice.RegisterExt.size(register) == width:
                candidates.append({f'op{index}_register': register})
    return candidates


def _address_registers(instruction) -> tuple[list[int], int, int]:
    memories = ice.InstructionInfoFactory().info(instruction).used_memory()
    address_32 = bool(memories and memories[0].address_size == ice.CodeSize.CODE32)
    if not memories:
        address_32 = any(reg != ice.Register.NONE and ice.RegisterExt.size(reg) == 4
                         for reg in (instruction.memory_base, instruction.memory_index))
        if instruction.memory_base == instruction.memory_index == ice.Register.NONE:
            address_32 = instruction.memory_displ_size == 4
    names = (('EAX', 'ECX', 'EDX', 'EBX', 'ESP', 'EBP', 'ESI', 'EDI',
              'R8D', 'R9D', 'R10D', 'R11D', 'R12D', 'R13D', 'R14D', 'R15D')
             if address_32 else
             ('RAX', 'RCX', 'RDX', 'RBX', 'RSP', 'RBP', 'RSI', 'RDI',
              'R8', 'R9', 'R10', 'R11', 'R12', 'R13', 'R14', 'R15'))
    return [getattr(ice.Register, name) for name in names], (ice.Register.EIP if address_32 else ice.Register.RIP), (ice.Register.ESP if address_32 else ice.Register.RSP)


def _operand_strategy(row: dict):
    """Generate structured operand mutations over their encoded value ranges."""
    encoded = bytes.fromhex(row['bytes'])
    instruction = ice.Decoder(64, encoded, ip=0x400000).decode()
    registers, ip_register, stack_register = _address_registers(instruction)
    inspection = inspect_operands(CandidateTemplate(row['iform'], row['iced_code'], encoded, row['bitness']))
    if inspection['unsupported_operands']:
        raise CandidateError(f"unsupported operand kinds: {inspection['unsupported_operands']}")
    fields = inspection['fields']
    strategies = [st.sampled_from(_register_bindings(encoded))]
    for field in fields:
        if field == 'memory_base':
            values = st.sampled_from([ice.Register.NONE, ip_register, *registers])
        elif field == 'memory_index':
            values = st.sampled_from([ice.Register.NONE, *(reg for reg in registers if reg != stack_register)])
        elif field == 'memory_index_scale':
            values = st.sampled_from([1, 2, 4, 8])
        elif field == 'memory_displacement':
            address_32 = ip_register == ice.Register.EIP
            size = 4 if address_32 else 8
            origin = 0x400000 + len(encoded) if instruction.is_ip_rel_memory_operand else 0
            values = st.integers(origin - (1 << 31), origin + (1 << 31) - 1)
            mask = (1 << 32) - 1 if address_32 else (1 << 64) - 1
            strategies.append(values.map(lambda value, size=size, mask=mask: {
                'memory_displacement': value & mask, 'memory_displ_size': size}))
            continue
        elif field == 'memory_displ_size':
            values = st.sampled_from([0, 1, 2, 4, 8])
        elif field.startswith('immediate8to'):
            values = st.integers(-128, 127)
        elif field == 'immediate32to64':
            values = st.integers(-(1 << 31), (1 << 31) - 1)
        elif field.startswith('immediate'):
            width = 8 if field.startswith('immediate8') else int(field[len('immediate'):])
            values = st.integers(0, (1 << width) - 1)
        elif field.startswith('near_branch'):
            suffix = row['iform'].rsplit('_', 1)[-1]
            bits = {'RELBRb': 8, 'RELBRw': 16, 'RELBRd': 32}.get(suffix)
            if bits is None:
                raise ValueError(f'unknown encoded branch width in {row["iform"]}')
            next_ip = 0x400000 + len(encoded)
            values = st.integers(next_ip - (1 << (bits - 1)), next_ip + (1 << (bits - 1)) - 1).map(
                lambda value: value & ((1 << 64) - 1))
        elif field.startswith('op') and field.endswith('_register'):
            continue  # Already covered by _register_bindings.
        else:
            raise CandidateError(f'no strategy for operand field {field}')
        strategies.append(values.map(lambda value, name=field: {name: value}))
    return st.one_of(*strategies)


def _source_fingerprint(source_root: Path) -> str:
    python_sources = sorted((source_root / 'extractor').glob('*.py'))
    if not python_sources:
        raise RuntimeError('source provenance file missing: extractor/*.py')
    paths = python_sources + [
        source_root / 'corpus/native/step_runner.c', source_root / 'corpus/BUILD.bazel',
        source_root / 'extractor/BUILD.bazel', source_root / 'flake.nix', source_root / 'flake.lock',
        source_root / 'MODULE.bazel', source_root / 'MODULE.bazel.lock',
        source_root / 'BUILD.bazel', source_root / '.bazelrc']
    fingerprint = hashlib.sha256()
    for path in paths:
        if not path.is_file():
            raise RuntimeError(f'source provenance file missing: {path}')
        fingerprint.update(str(path.relative_to(source_root)).encode() + b'\0')
        fingerprint.update(hashlib.sha256(path.read_bytes()).digest())
    return fingerprint.hexdigest()


def _encoding_database(root: Path, iform: str, encoded: str) -> DirectoryBasedExampleDatabase:
    key = hashlib.sha256((iform + '\0' + encoded).encode()).hexdigest()
    return DirectoryBasedExampleDatabase(root / 'native-encodings' / key)


def _row_worker(row: dict, args: argparse.Namespace, sender) -> None:
    """Keep each row's extractor and native attempts in a disposable process."""
    try:
        status, detail = _execute_row(row, args, lambda value: sender.send(('PROGRESS', value)))
        sender.send(('RESULT', status, detail))
    except Exception as exc:
        sender.send(('RESULT', 'INCOMPLETE', f'worker: {type(exc).__name__}: {exc}'))
    finally:
        sender.close()


def _execute_row(row: dict, args: argparse.Namespace, report_progress) -> tuple[str, str]:
    form, encoded = row['iform'], row['bytes']
    identify = xed_iform_decoder(args.xed)
    try:
        model = prepare_model(row, identify)
        operand_strategy = _operand_strategy(row)
    except Exception as exc:
        return 'INCOMPLETE', f'model: {type(exc).__name__}: {exc}'
    outcomes = Counter()
    reasons = {}
    # Each encoding has its own replay database because the dynamically
    # defined Python test otherwise has the same Hypothesis database key.
    database_root = Path(os.environ.get('HYPOTHESIS_STORAGE_DIRECTORY', '.hypothesis'))
    database = _encoding_database(database_root, form, encoded)

    @settings(max_examples=args.examples, deadline=None, report_multiple_bugs=False, database=database)
    @given(st.fixed_dictionaries({name: st.integers(0, 2**64 - 1) for name in REGISTERS}),
           st.integers(0, 127), operand_strategy, st.binary(min_size=64, max_size=64),
           st.one_of(st.just(0), st.integers(0x100000, 0x100fff), st.integers(0x200000, 0x200fff)),
           st.one_of(st.just(0), st.integers(0x100000, 0x100fff), st.integers(0x200000, 0x200fff)),
           st.binary(min_size=256, max_size=256))
    def check(values: dict[str, int], flags_value: int, bindings: dict[str, int],
              memory_bytes: bytes, fs_base: int, gs_base: int, xmm: bytes) -> None:
        try:
            candidate = prepare_model(row, identify, bindings=bindings) if bindings else model
        except Exception as exc:
            outcomes['INCOMPLETE'] += 1
            reason = f'candidate model: {type(exc).__name__}: {exc}'
            reasons.setdefault(reason, {'bindings': bindings})
            return
        registers = _candidate_registers(candidate.encoded, values, fs_base, gs_base)
        flag_bits = (0, 2, 4, 6, 7, 11, 10)
        flags_word = sum(((flags_value >> i) & 1) << bit for i, bit in enumerate(flag_bits))
        memory_data = bytearray(8192)
        memory_data[0x800:0x840] = memory_bytes
        memory_data[0x1800:0x1840] = memory_bytes
        memory = bytes(memory_data)
        try:
            capture = capture_step(args.bwrap, args.runner, tuple(args.runtime),
                                   candidate.encoded, registers, flags_word, memory,
                                   fs_base=fs_base, gs_base=gs_base, xmm=xmm)
            result = compare_native_state(candidate, capture, memory)
        except (NativeIsolationError, MemoryScopeError, CandidateError) as exc:
            result = {'status': 'INCOMPLETE', 'reason': f'{type(exc).__name__}: {exc}'}
        if result.get('status') not in ('MATCH', 'MISMATCH', 'INCOMPLETE'):
            result = {'status': 'INCOMPLETE', 'reason': 'comparator returned an invalid status'}
        outcomes[result['status']] += 1
        context = {'candidate': candidate.encoded.hex(), 'bindings': bindings,
                   'registers': registers, 'flags': flags_word, 'memory_bytes': memory_bytes.hex(),
                   'xmm': xmm.hex(), 'fs_base': fs_base, 'gs_base': gs_base}
        if result['status'] == 'INCOMPLETE':
            reasons.setdefault(result['reason'], context)
        elif result['status'] == 'MISMATCH':
            raise AssertionError(json.dumps({**context, 'comparison': result}, sort_keys=True))

    try:
        check()
    except AssertionError as exc:
        return 'MISMATCH', str(exc)
    except Exception as exc:
        return 'INCOMPLETE', f'campaign: {type(exc).__name__}: {exc}'
    if not outcomes:
        return 'INCOMPLETE', 'Hypothesis produced no examples'
    status = 'INCOMPLETE' if outcomes['INCOMPLETE'] else 'MATCH'
    return status, f'examples={sum(outcomes.values())} reasons={json.dumps(reasons, sort_keys=True)}'


class WorkerCleanupError(BaseException):
    pass


def _run_with_deadline(row: dict, args: argparse.Namespace) -> tuple[str, str]:
    context = multiprocessing.get_context('fork')
    receiver, sender = context.Pipe(duplex=False)
    process = context.Process(target=_row_worker, args=(row, args, sender))
    started = False
    try:
        process.start()
        started = True
        sender.close()
        deadline = time.monotonic() + args.row_seconds
        latest_input = None
        while True:
            if not receiver.poll(max(0, deadline - time.monotonic())):
                status = 'INCOMPLETE'
                detail = f'row deadline exceeded ({args.row_seconds}s); input={json.dumps(latest_input, sort_keys=True)}'
                process.terminate()
                break
            try:
                event = receiver.recv()
            except EOFError:
                status, detail = 'INCOMPLETE', 'model worker exited without a result'
                break
            if isinstance(event, tuple) and len(event) == 2 and event[0] == 'PROGRESS':
                latest_input = event[1]
                continue
            if isinstance(event, tuple) and len(event) == 3 and event[0] == 'RESULT':
                _, status, detail = event
                break
            status, detail = 'INCOMPLETE', 'row worker returned an invalid result'
            break
    except BaseException:
        if started and process.is_alive():
            process.terminate()
        raise
    finally:
        receiver.close()
        sender.close()
        if started:
            process.join(timeout=2)
            if process.is_alive():
                process.kill()
                process.join(timeout=2)
            if process.is_alive():
                raise WorkerCleanupError('row worker could not be stopped; aborting campaign')
    if status not in ('MATCH', 'MISMATCH', 'INCOMPLETE') or not isinstance(detail, str):
        return 'INCOMPLETE', 'row worker returned an invalid result'
    if process.exitcode != 0 and not detail.startswith('row deadline exceeded'):
        return 'INCOMPLETE', f'row worker exited with status {process.exitcode}'
    return status, detail


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('catalogue', type=Path)
    parser.add_argument('--xed', required=True)
    parser.add_argument('--bwrap', type=Path, required=True)
    parser.add_argument('--runner', type=Path, required=True)
    parser.add_argument('--runtime', action='append', type=Path, required=True)
    parser.add_argument('--examples', type=int, default=4)
    parser.add_argument('--row-seconds', type=int, default=30)
    parser.add_argument('--source-revision', required=True, help='immutable source revision for this run')
    args = parser.parse_args()
    if not 1 <= args.examples <= 100:
        parser.error('examples must be between 1 and 100')
    if not 1 <= args.row_seconds <= 300:
        parser.error('row-seconds must be between 1 and 300')
    if not re.fullmatch(r'[0-9a-f]{40}', args.source_revision):
        parser.error('source revision must be a full lowercase Git commit ID')
    if not Path(args.xed).is_absolute() or not Path(args.xed).is_file() or not os.access(args.xed, os.X_OK):
        parser.error('XED helper must be an executable absolute path')
    bubblewrap_command(args.bwrap, args.runner, tuple(args.runtime))
    require_bounded_cgroup()
    raw = args.catalogue.read_bytes()
    rows = [json.loads(line) for line in raw.splitlines()]
    if not rows:
        parser.error('catalogue is empty')
    cpu = {}
    try:
        for line in Path('/proc/cpuinfo').read_text().splitlines():
            key, _, value = line.partition(':')
            if key.strip() in ('vendor_id', 'cpu family', 'model', 'model name', 'stepping', 'microcode', 'flags') and key.strip() not in cpu:
                cpu[key.strip()] = value.strip()
    except OSError:
        pass
    versions = {}
    for package in ('iced-x86', 'hypothesis', 'pyvex', 'angr', 'z3-solver'):
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = 'unavailable'
    def digest(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    source_hash = _source_fingerprint(Path(__file__).resolve().parent.parent)
    print('RUN ' + json.dumps({'@context': {'@vocab': 'https://github.com/heartpunk/wruh/blob/main/docs/binary-census.md#'},
                               '@type': 'NativeDifferentialExecution',
                               'catalogue_sha256': hashlib.sha256(raw).hexdigest(),
                               'declared_source_revision': args.source_revision,
                               'source_files_sha256': source_hash,
                               'xed_sha256': digest(Path(args.xed)),
                               'runner_sha256': digest(args.runner),
                               'bubblewrap_sha256': digest(args.bwrap),
                               'rows': len(rows), 'platform': platform.platform(),
                               'machine': platform.machine(), 'cpu': cpu,
                               'packages': versions, 'examples': args.examples,
                               'input_bounds': {'rsp': '0x200800 only when used in a memory address',
                                   'address_registers': 'adjusted to target data page',
                                   'data_and_stack_pages': ['0x100000..0x100fff', '0x200000..0x200fff'],
                                   'extra_pages': 'up to two dynamically mapped, zero-initialized pages',
                                   'memory_pattern': 'same generated 64 bytes at offset 0x800 in each page',
                                   'fs_gs_bases': 'zero or an address in either observed page',
                                   'generated_flags': 'CF PF AF ZF SF OF DF',
                                   'xmm': 'all sixteen generated; other extended state inherited'},
                               'row_seconds': args.row_seconds,
                               'hypothesis_storage': os.environ.get('HYPOTHESIS_STORAGE_DIRECTORY', '.hypothesis')},
                              sort_keys=True), flush=True)
    counts = Counter()
    for row in rows:
        form, encoded = row['iform'], row['bytes']
        try:
            status, detail = _run_with_deadline(row, args)
        except Exception as exc:
            status, detail = 'INCOMPLETE', f'worker launch: {type(exc).__name__}: {exc}'
        counts[status] += 1
        print(f'{status} {form} {encoded} {detail}', flush=True)
    print(f'SUMMARY rows={len(rows)} forms={len({r["iform"] for r in rows})} '
          f'match={counts["MATCH"]} incomplete={counts["INCOMPLETE"]} '
          f'mismatch={counts["MISMATCH"]}', flush=True)
    if counts['INCOMPLETE'] or counts['MISMATCH']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
