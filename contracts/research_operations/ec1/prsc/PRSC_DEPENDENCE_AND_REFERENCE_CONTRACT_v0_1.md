# PRSC Dependence and Reference Contract v0.1

Authority effect: **NONE**. The EC1 `EvidenceDependenceGraph` remains the canonical owner of direct dependence edges. PRSC consumes it read-only and MUST NOT invent convenience edges, infer independence from graph absence, or replace owner ancestry semantics.

Conformance rules:
1. the persisted EC1 graph depth remains one; PRSC may filter owner edges to a candidate universe but never add an edge;
2. unlinked units are `INDEPENDENCE_UNKNOWN`, not independent replications;
3. inference blocks completely account for the declared candidate universe and do not split any owner direct edge;
4. leave-one-component/block diagnostics preserve the frozen block definition and do not redefine the candidate;
5. the primary reference path is dependency-preserving whole-block resampling with explicit seed and complete generated/rejected surrogate accounting;
6. negative-space controls are selected only at whole-block granularity where dependence would otherwise mix positive and control units;
7. HAC-style summaries are secondary only, require explicitly lawful order and explicit lag, and cannot create a universal `n_eff`, alpha, promotion threshold or freeze rule;
8. preservation failure blocks the reference result; invalid surrogates are never silently dropped.

Rollback is forward-only: quarantine a non-conformant PRSC optimized/secondary path and preserve the EC1 owner graph and reference oracle evidence.
