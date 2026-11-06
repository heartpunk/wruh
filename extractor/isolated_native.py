"""Fail-closed launcher for a native instruction runner inside bubblewrap.

The runner protocol is one bounded JSON request on stdin and one JSON response
on stdout. This module does not itself create or execute instruction bytes.
"""
from __future__ import annotations

import json
import resource
import subprocess
import tempfile
from pathlib import Path
from typing import Any


class NativeIsolationError(RuntimeError):
    """Sandbox setup, execution, or response validation failed."""


def bubblewrap_command(bwrap: Path, runner: Path, runtime: tuple[Path, ...]) -> list[str]:
    if (not bwrap.is_absolute() or not bwrap.is_file()
            or not bwrap.resolve().is_relative_to('/nix/store') or bwrap.name != 'bwrap'):
        raise NativeIsolationError('bubblewrap must be an existing Nix store bwrap executable')
    if not runner.is_absolute() or not runner.is_file():
        raise NativeIsolationError('runner must be an existing absolute path')
    mounts = []
    for path in runtime:
        resolved = path.resolve(strict=True)
        if not resolved.is_relative_to('/nix/store'):
            raise NativeIsolationError('runtime mounts must be Nix store paths')
        mounts.extend(['--ro-bind', str(resolved), str(resolved)])
    return [str(bwrap), '--unshare-all', '--unshare-user', '--disable-userns',
            '--cap-drop', 'ALL', '--clearenv', '--setenv', 'LANG', 'C',
            '--setenv', 'WRUH_NATIVE_SANDBOX', '1',
            '--new-session', '--die-with-parent', *mounts,
            '--ro-bind', str(runner.resolve(strict=True)), '/runner',
            '--proc', '/proc', '--dev', '/dev', '--size', '1048576',
            '--tmpfs', '/tmp', '--chdir', '/tmp', '--', '/runner']


def _require_job_limits(current: Path) -> None:
    for name in ('memory.max', 'memory.swap.max', 'pids.max', 'cpu.max'):
        values = (current / name).read_text().split()
        if not values or values[0] == 'max' or not values[0].isdigit():
            raise ValueError(f'finite per-job {name} is required')


def require_bounded_cgroup() -> None:
    """Require explicit per-job memory, swap, CPU and task bounds on cgroup v2."""
    try:
        lines = Path('/proc/self/cgroup').read_text().splitlines()
        paths = [line[3:] for line in lines if line.startswith('0::')]
        if len(paths) != 1 or not paths[0].startswith('/') or '..' in Path(paths[0]).parts:
            raise ValueError('no unique cgroup v2 path')
        root = Path('/sys/fs/cgroup')
        current = root / paths[0].lstrip('/')
        if not current.is_relative_to(root):
            raise ValueError('cgroup path escapes the unified hierarchy')
        _require_job_limits(current)
    except (OSError, ValueError, IndexError) as exc:
        raise NativeIsolationError(f'bounded cgroup required: {exc}') from exc


def _limits() -> None:
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_CPU, (2, 2))
    resource.setrlimit(resource.RLIMIT_AS, (256 * 1024 * 1024, 256 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_FSIZE, (1024 * 1024, 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))


def run_isolated(bwrap: Path, runner: Path, runtime: tuple[Path, ...],
                 request: dict[str, Any], *, timeout: float = 5.0) -> dict[str, Any]:
    """Invoke the runner only through bubblewrap, with bounded resources."""
    if timeout <= 0 or timeout > 30:
        raise NativeIsolationError('timeout outside permitted range')
    payload = json.dumps(request, separators=(',', ':')).encode() + b'\n'
    if len(payload) > 1024 * 1024:
        raise NativeIsolationError('request exceeds size limit')
    command = bubblewrap_command(bwrap, runner, runtime)
    require_bounded_cgroup()
    try:
        with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
            result = subprocess.run(command, input=payload, stdout=stdout, stderr=stderr,
                                    timeout=timeout, preexec_fn=_limits, check=False)
            stdout.seek(0)
            stderr.seek(0)
            output = stdout.read(1024 * 1024 + 1)
            error = stderr.read(1024 * 1024 + 1)
    except (OSError, subprocess.SubprocessError) as exc:
        raise NativeIsolationError(f'isolated runner failed: {exc}') from exc
    if result.returncode != 0:
        raise NativeIsolationError(f'isolated runner exited {result.returncode}: {error[:4096]!r}')
    if len(output) > 1024 * 1024 or len(error) > 1024 * 1024:
        raise NativeIsolationError('runner output exceeds size limit')
    try:
        response = json.loads(output)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise NativeIsolationError('runner returned invalid JSON') from exc
    if not isinstance(response, dict):
        raise NativeIsolationError('runner response must be a JSON object')
    return response
