# arpy provenance

- Package: `arpy`
- Version: `1.1.1`
- Upstream author: Stanisław Pitucha
- License: Simplified BSD; the notice is embedded in `arpy.py`
- Source artifact:
  `https://files.pythonhosted.org/packages/d2/15/09fbfc0d43b66a3845098377249539aa44edcd541e17eabe2e11b4e3855e/arpy-1.1.1.tar.gz`
- Source SHA-256:
  `3ec36309d2234648ef8dcd2118fe7d81c30195087e0353473546583f3434e776`
- Vendored file: `arpy.py`, copied byte-for-byte from the source artifact.

## Why this is vendored

CLE 9.2.214 requires arpy, but PyPI publishes version 1.1.1 only as a source
distribution. The extractor's Bazel dependency closure otherwise accepts
wheels only, so this pure-Python leaf is represented as a normal
repository-owned `py_library`. The CLE wheel's generated Bazel dependency is
patched to this target.

## Removal

Delete this directory and the corresponding CLE wheel override when the
selected Angr closure provides a pinned arpy wheel or no longer depends on
arpy.
