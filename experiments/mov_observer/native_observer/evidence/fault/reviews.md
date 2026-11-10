# Fault observation reviews

Technical Astra light review: source hashes match the build log; all 29 target
observations plus loader rejection passed with exit0 on the AVX guest. All four
fault examples exercised seeded extended-vector preservation. Sixteen raw fault
snapshots have expected sizes, and decoded siginfo matches logged metadata.
No remaining blocker.

Scope Astra light review: actual stopped state and partial effects are retained;
README matches the supported signal/RIP boundary. No proof, retry, or model
comparison expansion. No remaining blocker.

Review corrections were applied before final execution: SI_KERNEL address is
optional, asynchronous BUS_MCEERR_AO is rejected, and logs explicitly report
whether extended-vector checks ran. Both installed state paths remain unchanged.

Implementation checkpoint: 6f3ea9b97a4a2cc94eee499683aff068df09febb.
NixOS build/run: observer-fault-final-build.service.
AVX guest run: observer-fault-native-1.service, same existing VM104 and flake
closure documented in ../vector/. All four binary hashes match between hosts.
