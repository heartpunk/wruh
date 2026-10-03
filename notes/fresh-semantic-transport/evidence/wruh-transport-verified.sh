export PATH=/run/current-system/sw/bin:/usr/bin:/bin
export WRUH_AYXG_SOURCE=/tmp/ayxg-lean-fresh-transform-05d140bc
export LEAN_NUM_THREADS=4
cd /tmp/wruh-lean-fresh-transform-20261003 || exit 1
nix develop path:/tmp/ayxg-lean-fresh-transform-05d140bc --command bash -c 'lake build Wruh Wruh.FreshTransformExamples Wruh.FreshExtractionExamples && lake env lean notes/fresh-semantic-transport/ProofAudit.lean' > /tmp/wruh-transport-verified.log 2>&1
status=$?
printf '%s\n' "$status" > /tmp/wruh-transport-verified.exit
exit "$status"
