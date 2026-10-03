# Confirmed upstream scalar SSE rounding gap

Static lift of bytes `f2 0f 58 c1` (addsd xmm0,xmm1), using the qualified patched angr10 package, gives:

```
t1 = GET:V128(xmm1)
t2 = GET:V128(xmm0)
t0 = Add64F0x2(t2,t1)
PUT(xmm0) = t0
```

There is no read of sseround. Upstream angr10.0.1 `angr/engines/vex/claripy/irop.py:405–409`, scalar lowest-lane FP case, binds arithmetic to `partial(f, claripy.fp.RM.default())`. Consequently WRUH selector splitting cannot discover this dependency, and the extracted CPython addsd/mulsd edges contain RNE while sseround is unconstrained.

Independent artifact review confirmed the issue. Other reviewed artifact properties passed: identity, DAG topology, complete91 updates, FPnodes, and explicit transfer/relocation boundaries. This is upstream-model fidelity, not a claim of all-rounding hardware fidelity. No candidate binary was executed: shellcode bytes were lifted as data only.

A persistent user question requests authorization for a scoped upstream rounding repair. Dependent semantic repair and completion claim are paused; existing evidence is preserved.
