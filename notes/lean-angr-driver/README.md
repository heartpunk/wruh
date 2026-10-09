# Lean-led fresh extraction

`lake exe wruh-fresh` owns the function and instruction loop, decodes AYXG's
typed expression DAG in Lean, calls `Wruh.FreshExtraction.extractTagged`, and
writes the existing `ayxg-artifact-dag-v1` fresh bundle. The persistent Python
worker performs binary inventory and one angr successor step when Lean requests
an address. It does not assemble local edges or an STS.

The staged AYXG revision is `7b9e8c250ddd7fa1ad2831b21b877a03af70b857`,
the linear descendant that contains `Ayxg.QfAbv.JsonCodec` and the matching
Python expression codec. Stage it in a fresh checkout of this workspace along
with the existing angr dependency, then run from the WRUH root:

```sh
scripts/stage-ayxg ~/code/ayxg
scripts/stage-angr-nix ~/code/angr-nix
export WRUH_AYXG_SOURCE="$PWD/.dependencies/ayxg"
nix develop path:. --command nix develop "path:$WRUH_AYXG_SOURCE" --command \
  lake exe wruh-fresh --artifact /absolute/path/to/binary --root root_symbol \
  --output /absolute/path/to/fresh.json
```

The CLI also forwards `--provider`, `--manifest`, `--objects`, `--cfg`,
`--root-only`, and repeated `--candidate-root` options to the inventory worker.
`WRUH_PYTHON` can select a Python interpreter explicitly; otherwise the driver
uses the pinned angr interpreter from `GHOT_NIX_ANGR_ROOT` when available.

This entry point uses the operational fields of the existing symex-shaped
adapter. Its source-relation fields are proof premises, not a claim that angr
satisfies `SymexLaws`.
