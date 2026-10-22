#!/usr/bin/env bash
set -euo pipefail
./scripts/bootstrap
lake env lean -DwarningAsError=true notes/fresh-transform-core/ProofAudit.lean
lake env lean -DwarningAsError=true notes/fresh-semantic-transport/ProofAudit.lean
