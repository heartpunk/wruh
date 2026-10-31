from concurrent.futures import Future

import pytest

from extractor.generated_hints import DependencyHint, HintCache, HintKey, extract_hint


class ImmediateExecutor:
    def __init__(self):
        self.calls = []

    def submit(self, function, key):
        self.calls.append(key)
        future = Future()
        try:
            future.set_result(function(key))
        except Exception as error:
            future.set_exception(error)
        return future


def test_cache_reuses_exact_encoding_and_keeps_provenance_separate():
    executor = ImmediateExecutor()
    cache = HintCache(executor, lambda key: DependencyHint(frozenset({"rdi"}), frozenset({"rax"})))
    first = HintKey(b"\x48\x89\xf8", 0x400000, "revision-a")
    second = HintKey(first.encoding, first.source, "revision-b")
    assert cache.enqueue(first) is cache.enqueue(first)
    assert cache.enqueue(first).result().reads == {"rdi"}
    cache.enqueue(second)
    assert executor.calls == [first, second]


def test_extract_mov_register_dependency_from_wruh():
    # mov %rdi,%rax: extraction runs WRUH on the real bytes, not a table.
    hint = extract_hint(HintKey(b"\x48\x89\xf8", 0x400000, "test"))
    assert "rdi" in hint.reads
    assert "rax" in hint.writes
    assert "rbx" not in hint.writes


def test_failed_extraction_is_not_reinterpreted_as_a_hint():
    cache = HintCache(ImmediateExecutor(), lambda key: (_ for _ in ()).throw(ValueError("unsupported")))
    with pytest.raises(ValueError, match="unsupported"):
        cache.enqueue(HintKey(b"\x90", 0x400000, "test")).result()
