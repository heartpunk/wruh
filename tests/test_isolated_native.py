"""The launcher must fail closed and always invoke bubblewrap."""
from pathlib import Path
from unittest.mock import patch

from extractor.isolated_native import NativeIsolationError, run_isolated


def test_invalid_bubblewrap_does_not_run_a_candidate():
    with patch('extractor.isolated_native.subprocess.run') as launch:
        try:
            run_isolated(Path('/no/bwrap'), Path('/no/runner'), (), {})
        except NativeIsolationError:
            pass
        else:
            raise AssertionError('missing bubblewrap was accepted')
        launch.assert_not_called()


def test_oversized_request_does_not_run_a_candidate():
    with patch('extractor.isolated_native.subprocess.run') as launch:
        try:
            run_isolated(Path('/no/bwrap'), Path('/no/runner'), (), {'x': 'a' * (1024 * 1024)})
        except NativeIsolationError:
            pass
        else:
            raise AssertionError('oversized request was accepted')
        launch.assert_not_called()


def test_each_resource_has_a_finite_job_limit(tmp_path):
    from extractor.isolated_native import _require_job_limits
    limits = {'memory.max': '1048576', 'memory.swap.max': '0',
              'pids.max': '64', 'cpu.max': '100000 100000'}
    for name, value in limits.items():
        (tmp_path / name).write_text(value)
    _require_job_limits(tmp_path)
    for name in limits:
        (tmp_path / name).write_text('max')
        try:
            _require_job_limits(tmp_path)
        except ValueError:
            pass
        else:
            raise AssertionError(f'unbounded {name} was accepted')
        (tmp_path / name).write_text(limits[name])
