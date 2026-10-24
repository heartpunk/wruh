# Lua 5.5.1 WRUH census (2026-10-17)

Source: MBP GUI Codex task `01a14b31-ee3c-71f0-a73e-6f08616ffae1`, “do a lua extraction w/wruh. latest lua from nixpkgs. use abraxas for compute.” Its rollout is `~/.codex/sessions/2026/10/17/rollout-2026-10-17T11-48-45-01a14b31-ee3c-71f0-a73e-6f08616ffae1.jsonl` on MBP.

The retained provenance says the target was Lua 5.5.1 from Nixpkgs `8e1eaba1dbd6595380d0cf78d0ff93c1ce1871d8`, binary `/nix/store/w8ir5gi155fiabnysnr6372fn1zsw45x-lua-5.5.1/bin/lua`. WRUH source was `16d77877512d97fad0622a7a6ac401cf8b2dd538` (open PR #2 tip); AYXG was `5106df06d92620da810c325b8779ce97a14f7f0e` (open PR #1 tip). Compute host: Abraxas.

All 733 distinct sized function symbols were attempted. 518 passed Wruh CFG inventory, 215 were blocked there; 498 completed fresh extraction and 20 were blocked in fresh extraction. Thus 498/733 (67.9%) artifacts, 235/733 blocked. First-observed categories: CFG call fallthrough crossing function extent 209; unsupported jump kind 6; AMD64 SMT conversion 16; symbolic register-file selector 2; unsupported Z3 operator 2. The merged artifact had 498 corresponding CFG roots, 223,916 expression DAG nodes, and 2,533,413 expression roots. References were structurally in range; unresolved/indirect/blocked calls remained open. Artifact SHA-256: `58424d5c3ef0c3921735a319d04a652eda653b8a23468da6dc2f0ff0b54c1aad`.

Primary evidence is on MBP: `~/workspaces/wruh-lua-extraction/artifacts/lua-full-fresh.provenance.txt`, `lua-full-attempt-manifest.json`, `lua-full-fresh.json`, and `function-logs/`.
