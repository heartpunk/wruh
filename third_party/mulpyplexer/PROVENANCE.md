# mulpyplexer provenance

- Package: `mulpyplexer`
- Version: `0.09`
- Upstream author: Yan Shoshitaishvili
- License: BSD-3-Clause; see `LICENSE`
- Source artifact:
  `https://files.pythonhosted.org/packages/d7/6f/f036d4fb9f5a511262345bb18215c70fa69a250aca2e5ffe1a9c7e4cb85c/mulpyplexer-0.09.tar.gz`
- Source SHA-256:
  `144e9e9bf66d3988f60542c9d3d4c94857438f7908f60e53f4c1cb1622fbbd30`
- Vendored files: `mulpyplexer.py`, copied byte-for-byte from the source
  artifact, and `LICENSE`, copied with only the final redundant blank line
  normalized.

## Why this is vendored

Angr 9.2.214 requires mulpyplexer, but PyPI publishes version 0.09 only as a
source distribution. The extractor's Bazel dependency closure otherwise
accepts wheels only, so this tiny pure-Python leaf is represented as a normal
repository-owned `py_library`. The Angr wheel's generated Bazel dependency is
patched to this target.

## Removal

Delete this directory and the corresponding Angr wheel override when the
selected Angr closure provides a pinned mulpyplexer wheel or no longer depends
on mulpyplexer.
