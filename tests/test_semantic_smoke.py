"""Collect the existing semantic smoke checks in the standard test runner."""



def test_angr_smt_boundary():
    from extractor.angr_smt_smoke import check

    check()


def test_architecture_semantics():
    from extractor.architecture_checks import check

    assert check()["status"] == "PASS"


def test_open_transfers():
    from extractor.open_transfers_smoke import main

    main([])


def test_open_object_fixture(tmp_path, monkeypatch):
    from pathlib import Path
    from extractor.open_object_smoke import main

    def unexpected_compiler_lookup(*args, **kwargs):
        raise AssertionError("checked-in fixtures must not require a host compiler")

    monkeypatch.setattr("extractor.open_object_smoke.shutil.which", unexpected_compiler_lookup)
    root = Path(__file__).absolute().parents[1]
    fixture = root / "corpus" / "open-transfers"
    main(["--fixture-directory", str(fixture / "fixture"),
          "--entry", str(fixture / "entry.c"),
          "--library", str(fixture / "library.c"),
          "--output", str(tmp_path / "result.json")])
