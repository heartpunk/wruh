# Generated native differential testing (draft)

Revizor is pinned in the flake. `extractor/revizor_generate.py` accepts a
Revizor ISA description and configuration, including its instruction exclusion
list, and generates assembled test objects. The interface does not impose an
additional instruction allowlist or select an architecture.

Run in the development shell with, for example:

```
PYTHONPATH="$WRUH_REVIZOR_SOURCE" "$WRUH_REVIZOR_PYTHON" \
  extractor/revizor_generate.py --isa path/to/isa.json --config path/to/config.yaml \
  --output path/to/cases --count 10
```

The earlier hand-generated x86 prototype is preserved in the branch history.
`extractor/revizor_differential.py` is an initial x86 execution adapter; it
compares the existing return-value and memory observations, not full machine
state. Its correctness and end-to-end results are being checked. It does not
make the generator interface x86-specific.

Initial experiment: ten 100-instruction cases from Revizor's x86 test ISA
fixture generated and assembled. On main, all ten stopped at locked operations
with an overlapping-CFG-block extraction error; they did not reach a native
comparison. The earlier prototype's four matches are not Revizor results.
Revizor itself reserves registers and instruments memory/faults by default.

`extractor/revizor_differential.py` accepts a generated `program.asm` (and its
adjacent `program.o`). It composes fresh paths and asks SMT for distinct input
pairs satisfying their guards before native execution. `--samples` defaults to
1,000 per program. It records the binary, solved input batch, path statuses,
and each comparison outcome. Solver timeouts, incomplete extraction, and
incomplete execution remain explicit rather than being reported as matches.

The current native adapter compares the returned value and designated scratch
memory. Invoking the composer here supplies smoke coverage of path composition;
the native comparison does not independently assert correctness of the
composition algorithm. A four-input pilot against the #57 source with the #58
AYXG pin matched all four observations. Two other composed paths timed out in
the initial five-second solver window. The ten-program,
1,000-input-per-program campaign is running separately.

A diagnostic retried those two case-0 guards with a 30-second per-query bound
and Z3 statistics. Both were satisfiable (16.8 and 20.9 seconds) and their
native comparisons matched. The diagnostic saw roughly 3.4–3.8 million Boolean
variables, hundreds of thousands of array expansion axioms, and 16–43 million
Z3 resource-limit units in those checks. The default bound is now 30 seconds;
the already-running campaign retains its original five-second snapshot, so its
unresolved paths must be interpreted with that limit.
