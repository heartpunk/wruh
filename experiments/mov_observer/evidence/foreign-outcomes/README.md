# Foreign returned outcomes

Typechecked source: `085c0cdf1155595d0eefb4e8b9f6076255e66ee9`.

Pinned runtime inspection (../lean-runtime-abi) identified returned IO.Error
as a missing case in the call execution skeleton. Bridge now carries
`Except IO.Error DecodedReply`, with decoded Reply or exact malformed bytes.
Wire.ForeignReturnMatches independently specifies all returned IO outcomes.
WholeObserver retains same-operation/phase evidence for runtime errors and
malformed replies, separate from native errno replies. This does not prescribe
recovery or imply all runtime aborts become IO errors.

Integrated Lean 4.34.0 typecheck passed on NixOS, unit
observer-spec-085c0cdf.service under fleet-build.slice, 2 GiB/no swap/one CPU.
All modules Protocol, ContractEquivalence, NativeBoundary, Bridge, Wire,
Transfer, VectorProtocol, LegacyFp, FaultProtocol, WholeObserver passed.
Existing vector unnecessarySimpa warnings remain. Git metadata was preserved
in the snapshot; no source was edited remotely.

Terra 6.1 high agent /root/review_reply_terra reviewed 64c33739 and found that
malformed returns had not propagated across all interfaces. The correction
085c0cdf passed its source-only re-review. A final comment-only correction lists
malformed replies alongside the other failure cases; no logical change.

These are obligations, not implementation or proofs. Ownership transfer,
actual foreign-return/decoder/event binding, failure causality, external
resource premises and whole-observer completion remain open.
