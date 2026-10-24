# Apache HTTP Server compiled CFG fixtures

These small fixtures contain unchanged machine-code excerpts from Apache HTTP
Server 2.4.69, plus WRUH-generated CFG records for regression tests. The bytes
come from the Nixpkgs `apache-httpd` binary built from the `2.4.69` source
release with symbols retained. The exact ELF SHA-256 is
`7a850a2d913a2bcbc4a87b809b5362bc0a23a005e5590137abf42e997d7ca2d9`; the
Nixpkgs revision was `02c087f3fe673c9e317f206a627cb6b910336dbe`.

| Function | Apache source file | ELF address | Size |
| --- | --- | ---: | ---: |
| `ap_fini_vhost_config` | `server/vhost.c` | `0x440c80` | 1797 bytes |
| `ap_pass_brigade_fchk` | `server/util_filter.c` | `0x44b180` | 594 bytes |

Each `.bin` file is the byte range at the symbol's address and size. Its JSON
file records the same binary digest, source path, function extent, and the CFG
blocks recovered by WRUH. The tests verify the machine bytes against every
decoded instruction record and pass the real blocks through the CFG validator.
The fixtures are data and are never executed.

The two source files identify the Apache License, Version 2.0 in their headers.
The release's `LICENSE` and `NOTICE` are copied here verbatim to accompany the
compiled excerpts. See those files for the applicable terms and attribution.
