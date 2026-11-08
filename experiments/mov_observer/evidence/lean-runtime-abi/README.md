# Pinned Lean ABI investigation

Inspected installed Lean 4.34.0, upstream commit
`293d5d0c0c3f3dded4688b3ccd6a33939ac5102b`, Linux x86-64.
Exact installed file hashes and store path are in source-identity.txt.
This is source evidence, not a new typecheck or a proof of the bridge.

The upstream source counterpart of include/lean/lean.h is src/include/lean/lean.h.
Relevant installed declarations and lines:

- lean.h:158–188: standard arguments consume an ownership reference; borrowed
  arguments do not. Standard results transfer responsibility for consuming the
  returned reference. Pointer typedefs document, rather than enforce, this rule.
- lean.h:203–209,1129–1153: scalar arrays have a header, size, capacity, and byte
  storage. Allocation sets element size; ByteArray uses element size one.
  Only initialized size bytes are wire payload. Capacity is not payload length.
  Do not hardcode C struct byte offsets without validating the target ABI.
- lean.h:3035–3059: IO result success tag is zero, error tag is one; both hold
  one object in field zero. get_value/get_error return borrowed references.
  take_value increments the value then decrements the result wrapper; it is
  not sound to free a wrapper and keep a merely borrowed child reference.
- Init/System/IO.lean:62,82,140: IO is EIO IO.Error; toBaseIO exposes Except.
  A returned IO error is distinct from a successful ByteArray containing the
  bridge's encoded `.failed errno transferred` reply.
- lean.h:1171–1173: empty byte-array construction can invoke the runtime OOM
  panic path. Source inspection does not establish that all allocation failures
  become IO.Error, nor that a bounded wire size guarantees enough memory.

## Consequences for the unfinished boundary specification

1. Bind request payload buffers to actual scalar-array initialized bytes, not
   the object header or capacity; retain the borrow through every call prefix.
2. Specify transfer of the owned IO-result root and lifetime of its contained
   value/error, including the caller's extraction operation. Existing buffer
   frames alone do not describe this ownership handoff.
3. Cover BOTH runtime IO outcomes. At investigation baseline `0a221f1a115ca89298f39aad7df3c92029bb90f4`,
   ForeignAPI/Execution recorded Reply returns but lacked an explicit IO.Error
   return branch in its execution relation. Errors must not be silently coerced into native errno
   replies, omitted as absent paths, or fabricated into observations.
4. Separate returned IO errors from runtime abort/OOM paths. The promised finite
   classified completion must either include the agreed external resource/runtime
   premises or account for abnormal termination at an outer boundary. Do not
   silently assume our allocation and glue code always succeed.

The exact ownership and return obligations can be stated before observer
implementation. The executable artifact binding and its proof remain separate.

The returned-error representation gap above was addressed by specification
commits `64c337392424f5d762589d35dd2a6f6e38e2e964` and
`085c0cdf1155595d0eefb4e8b9f6076255e66ee9`. Ownership and actual foreign
execution binding remain open; see evidence/foreign-outcomes for validation.
