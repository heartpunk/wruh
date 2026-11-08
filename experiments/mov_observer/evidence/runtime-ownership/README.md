# Shared-state runtime ownership

Checked source: `7bbe657ff5691b9019bbc5b8e79b26a2af56af73`.
RuntimeOwnership.lean adds ownership Props, not a runtime implementation.
Logical reference rights and accessor views use the existing HostState
allocation incarnations. No physical reference-count equality is presumed.

The contract names the acting party, allows authorized borrowed input use
without consumption of caller ownership, requires live protection for child
uses, and exposes retain/release/transfer/allocation actions. The raw foreign
return boundary requires transfer of an owned wrapper from bridge to caller;
subsequent caller extraction may release the borrowed request and wrapper.
Every final decoded outcome is linked to the retained raw return. The same
execution/host projection supplies borrow, lifetime, memory frame and total
termination obligations. Constant foreign-segment restriction ends borrowing
at the raw boundary, not at the later decoded return.

Terra 6.1 high /root/review_reply_terra reviewed the initial source and found
missing actor authority, an overlong borrowing interval and vacuous raw-return
coverage. These were corrected. It then found missing parameter declarations;
the first remote check also failed on those editing errors. Correction 7bbe657f
passed the source re-review and integrated Lean 4.34.0 check. All eleven modules,
including existing Protocol/ContractEquivalence, passed; prior vector style
warnings remain. check_pipeline.sh syntax passed and copies/checks the module.

NixOS unit observer-spec-7bbe657f.service ran under fleet-build.slice with 2 GiB,
zero swap and one CPU. Git metadata accompanied the immutable snapshot; no
remote repository-source edits. Validation output/resources are attached.

Still open: actual runtime layout/accessor/raw-child value correspondence,
complete action/use/event binding, legitimate output permissions, full source
and whole-observer linkage, and external progress/resource premises. The
contract does not establish any of those merely by naming projections.
No observer implementation, correctness proof, push or merge was performed.
