# BCWT-R2 exact-head complete-sweep trigger

Programme: `OVC-BCWT-v0.1`  
Packet: `BCWT-R2`  
Authority effect: **NONE**  
Scientific effect: **NONE**

This non-executable assurance marker intentionally places the BCWT-R2 candidate in the repository's existing `tools/ci/**` FINAL_HEAD risk class so the canonical complete repository sweep, pytest/unittest parity, VIT routing, runner parity and merge-readiness machinery are exercised on the exact candidate head.

It does not alter the test selector, workflow, registry, dependency set, runtime behavior, active stack, OPT-C/OPT-D authority, scientific semantics, source admission, or any production code. It may be retained as packet assurance provenance after integration.
