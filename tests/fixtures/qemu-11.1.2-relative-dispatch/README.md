# QEMU 11.1.2 relative dispatch regression

`fixture.json` contains the original instruction bytes from
`parts128_uncanon_normal.constprop.0`, canonical `[0x3a8ee0, 0x3a8f2e)`,
and eight original signed little-endian 32-bit entries from `.rodata`
`[0xbadacc, 0xbadaec)`. The fixture uses the census loader's +0x400000
rebase, hence entry `0x7a8ee0` and table `0xfadacc`. Machine bytes are
unchanged; the RIP-relative LEA still addresses the rebased table.

Source: QEMU 11.1.2, binary SHA-256
`210c36c5e6474e3cff30a2df2da3cef8ad7fd7c4112e597ba8b33ed7fdd92842`,
NixOS artifact
`/nix/store/h4i7pqhgs0xngsj43nv2g0z41g9n7kid-wruh-census-qemu-host-cpu-only/binary`.
Read directly with GNU objdump 2.46 on 2026-11-13, using `-d
--start-address=0x3a8ee0 --stop-address=0x3a8f2e` and `-s -j .rodata
--start-address=0xbadacc --stop-address=0xbadaec`.

QEMU is distributed under GPL-2.0; see https://www.qemu.org/docs/master/about/license.html.
This small extracted regression preserves the original code and data rather
than substituting a synthetic dispatch sequence. The test reconstructs only
the code/table slice, not the complete function or executable.
