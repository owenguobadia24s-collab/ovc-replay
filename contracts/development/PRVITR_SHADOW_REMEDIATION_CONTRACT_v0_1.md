# PR/VIT Live Remediation Shadow Contract v0.1

**Programme:** `OVC-PRVIT-LIVE-REMEDIATION-CONFORMANCE-v0.1`  
**Authority source:** operator `PASS` at `PRVIT-G-CUTOVER-READINESS`.  
**Mode:** `DUAL_READ_SHADOW_REMEDIATION`.

## Constitutional separation

The existing live PR/VIT/SIQ/GRT admission path remains authoritative until the operator-reserved `PRVITR-G-LIVE-SWITCH` gate. This programme may implement and qualify corrected admission objects, selective recovery, idempotency, Git-native ancestry proof and non-churning closeout in shadow. It may not change the required GitHub status context, repository ruleset, first live admission verifier, physical VIT control class, or any scientific/exposure authority.

The corrected ordering is: PIP identity -> typed payload-scoped A0 assurance generation -> VIT placement -> exact-tree GRT/base-sensitive assurance -> immutable integration admission receipt -> existing serialized physical gateway only after later switch authority -> narrow post-materialisation receipt.

A placement failure MUST NOT rewrite an established A0 result as `FAIL`. Typed assurance states are `PASS`, `FAIL`, `BLOCKED_UPSTREAM`, `NOT_APPLICABLE`, `STALE`, `SUPERSEDED`, and `CAPACITY_FAILED`.

PR number, branch name, PR title/body/labels, worker and workflow rerun are provenance. They are not logical PIP identity. Decision-bearing VIT lineage is an immutable content-addressed record; PR prose may carry only a pointer to it in the corrected shadow model. Every rerun creates a new immutable `IntegrationAssuranceGeneration`; prior generations remain addressable.

Unchanged PIP + unchanged authority/dependency frontier under path-disjoint main movement => `PLACEMENT_RECOMPUTE_ONLY`, A0 reuse allowed, placement-sensitive assurance renewed. Semantic dispatch is idempotent on `(programme_id, packet_id, pip_id)`. Normative ancestry is local Git graph proof; GitHub compare APIs are diagnostic. Post-write commit identity is bound in a separate `PhysicalMaterialisationReceipt`; it does not mutate the qualified PIP.

Hard denies: no required-check/ruleset change; no live admission switch; no physical VIT control broadening; no force-push/history rewrite; no destructive cleanup; no scientific/model/selector/semantic promotion; no Validation/publication/probability/risk/exposure/execution/agent-write authority; no consumption of PR #1106 authority.
