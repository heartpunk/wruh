# QuickJS WRUH census (2026-10-17)

Source: MBP GUI Codex task `01a14b37-87e1-7f51-b186-c9105ce74236`, “do a quickjs extraction w/wruh. latest lua from nixpkgs. use shire for compute.” Workspace: `~/Documents/Codex/2026-10-17/do-a-lua-extraction-w-wruh`; rollout: `~/.codex/sessions/2026/10/17/rollout-2026-10-17T11-54-52-01a14b37-87e1-7f51-b186-c9105ce74236.jsonl` on MBP.

QuickJS pin: `3d5e064e9dd67c70f7962836505a7fa067bf0a4e`; Nixpkgs `8e1eaba1dbd6595380d0cf78d0ff93c1ce1871d8`; WRUH `16d77877512d97fad0622a7a6ac401cf8b2dd538`. The pinned target was built with debug symbols. The run attempted all 1,420 inventoried functions exactly once; 1,019 yielded artifacts, 401 had recorded exceptions/issues (71.8% artifact rate). Reported first-failure groups: static CFG issues 240; Z3 bit-vector/SMT errors 138; noncanonical function-owner IDs 18; unsupported `bvsdiv` 5. The final report says the artifact archive audit verified all 1,019 artifact files against recorded hashes.

Primary files remain on MBP at `~/Documents/Codex/2026-10-17/do-a-lua-extraction-w-wruh/outputs/quickjs-wruh/`: summary JSON, function inventory, per-function CSV, archive, run script, README, and pinned flakes. Summary SHA-256: `90a717f474aa4859edd5e90f109f3428a7febca7e9b9e7da62a8ef0da68bb64e`; artifact archive SHA-256: `14d66e20f8208919b08890adf289313fc1d9c9ee88aea723c74326fe72335903`.

The task title says “latest lua” while explicitly requesting QuickJS; these metrics are QuickJS results.
