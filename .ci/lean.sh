#!/usr/bin/env bash
set -euo pipefail
lake exe cache get
lake build Wruh wruh-fresh
lake env lean -DwarningAsError=true notes/fresh-transform-core/ProofAudit.lean
lake env lean -DwarningAsError=true notes/fresh-semantic-transport/ProofAudit.lean
