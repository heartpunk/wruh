#!/usr/bin/env bash
set -euo pipefail
./scripts/bootstrap
lake env lean -DwarningAsError=true notes/fresh-transform-core/ProofAudit.lean
lake env lean -DwarningAsError=true notes/fresh-semantic-transport/ProofAudit.lean

WRUH_LEAN_EXE="$PWD/.lake/build/bin/wruh-fresh" ./scripts/wruh-env python3 -m pytest tests/test_loaded_image_semantics.py -k test_main_entrypoints_publish_same_symbols_and_transitions -v
