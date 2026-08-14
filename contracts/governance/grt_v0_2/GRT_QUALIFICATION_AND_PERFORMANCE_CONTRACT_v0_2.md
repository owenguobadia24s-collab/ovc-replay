# GRT v0.2 Qualification & Performance Contract — WP3E

Status: **SHADOW / PRE-G2**. Authority effect: **NONE**.

Qualification is a conjunction across A1–A8. Every axis must PASS, with zero mandatory mutation survivors, zero reference/incremental semantic differences, zero unresolved enforcement false negatives and zero blocking false positives. Restart/checkpoint, platform, capacity/fault and shadow-CI evidence must also PASS. Qualification is evidence only and never activates GRT.

`GRTPerformanceBudget` is measurement-before-freeze. The implementation has no default runtime, memory, cache, evidence-size, repository-scale or capacity threshold. Each GRT-FAST, GRT-EXACT, GRT-REFERENCE, proof-renewal and readiness surface requires at least 20 measured samples in the exact qualification environment before p50/p95/max can be frozen. Insufficient evidence fails closed with `GRT_PERFORMANCE_MEASUREMENT_INSUFFICIENT`.

Capacity pressure may change physical execution strategy only; it cannot sample, reduce precision, omit required partitions, weaken rule semantics or manufacture PASS. A measured capacity threshold produces `CAPACITY_EXCEEDED`/`NOT_EVALUABLE` in the caller and preserves evidence.

GRT2-G2 may PASS automatically only when qualification PASS, the complete numeric performance budget is frozen from measured evidence, and pre-enforcement transition debt is zero. G2 PASS grants no G2.5/G3 enforcement authority.
