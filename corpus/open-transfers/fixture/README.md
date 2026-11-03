# Open-object test data

These AMD64 ELF64 files are inert input to CLE/angr. Tests load and inspect them;
they never execute them and do not need a host C compiler. `entry.c` and
`library.c` in the parent directory are their sources. The test checks source
and binary SHA-256 hashes against `manifest.json` before loading either file.

## Provenance and regeneration

Generator commit: `3a39d123ddd67ae5d8a12c9869870cfe84b6491d` in `heartpunk/wruh`.
The generator is committed before the generated data, avoiding a circular
commit identity. `manifest.json` records the exact immutable Nix runtime,
target, commands (with Bazel location substitutions), and input/output hashes.
`compiler.txt` records compiler/linker versions and resolved store paths.

Regeneration requires the qualified worker-runtime closure recorded in the
manifest to be installed on the build host (including its compiler and linker).
`flake.nix` names this existing store path; `nix develop` does not provision it.
Use an already qualified Linux worker, or copy the closure from one with
`nix copy --from ssh://QUALIFIED_HOST /nix/store/v1g3lwbbarxyrdl4b6b2mgdgdx9b7v9q-ghot-reapi-worker-runtime`.
The Bazel analysis host also needs the repository's existing pinned native
runtime inputs. Once those prerequisites are present, use a clean checkout
of the generator commit on x86-64 Linux:

```sh
git checkout 3a39d123ddd67ae5d8a12c9869870cfe84b6491d
nix develop --no-write-lock-file --command \
  bazel build //corpus/open-transfers:generate_fixture
```

The outputs are in `bazel-bin/corpus/open-transfers/generated/`:
`fixture.elf`, `libfixture.so`, and `compiler.txt`. Compare their SHA-256 hashes
with the manifest from the data commit. The target explicitly selects Linux
and x86-64, uses the declared Nix runtime's Clang and linker, passes an explicit
LLVM target, disables linker build IDs, and links without libc. It is manual:
ordinary wildcard builds do not regenerate or replace reviewed test data.
The existing qualified REAPI profile can also schedule this Linux target.

For an intentional source/toolchain update, first commit the generator and
sources, generate from that commit, then copy all three outputs here and
update the manifest, generator commit above, and hashes in a subsequent commit.
Run `nix develop --command pytest tests/test_semantic_smoke.py` and
`nix develop --command bazel test //tests:python_tests` before review. The Bazel
Python target remains Linux-only because of its existing native runtime;
standalone pytest consumes the same fixture data on macOS without compilation.
