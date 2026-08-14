# GRT v0.2 Integration Proof Contract — WP3D

Status: **SHADOW / NON-ENFORCING PRE-G3**. Authority effect: **NONE**.

`GRTIntegrationContext` pins predecessor main commit/tree, candidate head commit/tree, merge strategy, prospective integration tree, Constitution hash, runtime/scanner hashes and current DebtFloor identity. Before G3, DebtFloor is absent and WP3D is forbidden from creating generation 0.

`ConformanceProof` is valid only for the exact context and evidence hashes. `GRTIntegrationReadiness` compares current main/head/prospective-tree identities with the proof and returns `READY` only on exact PASS-context identity; movement is typed as `NON_INTERACTING`, `IMPACTING_REUSABLE`, `IMPACTING_RECOMPUTE`, `CONFLICTING`, `CONSTITUTION_CHANGED` or `HEAD_MOVED`. A stale proof is renewed; the stable-main guard is never weakened.

Layer cache keys contain only semantic input hashes, runtime/scanner/Constitution/registry identities and serializer profile. Branch names, PR numbers, timestamps and runner IDs are non-semantic metadata. Ambiguous impact closure escalates to full reference; capacity failure must return a fail-closed typed state in the caller rather than truncate semantics.

Post-merge receipt finalization requires actual merge tree == proved integration tree. A mismatch is an incident. Pre-G3 receipts cannot create a DebtFloor. DSAI/PDC continue to own execution, required checks, queueing and merge eligibility; this module supplies shadow GRT proof semantics only until G3 operator activation.
