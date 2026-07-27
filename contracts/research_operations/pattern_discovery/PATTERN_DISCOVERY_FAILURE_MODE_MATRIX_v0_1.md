# Pattern Discovery Failure-Mode Matrix v0.1

Trigger precedence affects queue presentation and closure-profile choice only. All TriggerEvents remain preserved.

Display precedence:

1. `QUALITY_OR_INCIDENT`
2. `CROSS_SCALE_CONFLICT`
3. `STRUCTURAL_TRANSITION`
4. `PERSISTENCE_OR_INSTABILITY`
5. `NOVELTY`
6. `RECURRENCE`
7. `CONTROL`

If two triggers require incompatible closure contracts, create separate candidates subject to caps.

| Failure | Candidate transition | Required effect |
|---|---|---|
| Source C2 record quarantined before review | `* -> INVALID_SOURCE_QUARANTINED` | Exclude from clustering; retain audit; permit Incident action |
| Source quarantined after evidence freeze | Evidence remains immutable | Append linked admissibility incident/withdrawal decision; never delete evidence |
| Missing 15M or 2H source interval | `OPEN/ACCUMULATING -> CENSORED_GAP` | Do not continue the same path across the gap |
| Temporary processing delay with intact late arrival | `OPEN -> OPEN_PENDING_INPUT` | Resume only after chronology and checksum validation |
| Parent context unavailable | Trigger result `NOT_EVALUABLE_PARENT_CONTEXT` | No cross-scale candidate; independent structural trigger may remain |
| Contradictory triggers on same bar | Preserve all TriggerEvents | Display primary by precedence; keep contradictions attached |
| Duplicate structural candidate | `DETECTED -> SUPPRESSED_DUPLICATE` | Attach trigger reference to existing compatible candidate |
| Quality and structural trigger coexist | Display quality/incident primary | Structural trigger remains secondary; invalid quality may block promotion |
| Maximum duration reached | `OPEN/ACCUMULATING -> READY_FOR_REVIEW:CENSORED_MAX_DURATION` | Completion remains explicitly censored |
| Parent container replaced | `OPEN/ACCUMULATING -> CENSORED_CONTEXT_CHANGE` | New candidate may open under new parent identity |
| Fingerprint build fails | `READY_FOR_REVIEW -> READY_FINGERPRINT_FAILED` | Exclude from clustering; preserve Incident path |
| Mixed fingerprint versions | Reject ClusterVersion build | Keep previous current cluster version |
| Queue hard cap reached | Candidate `SUPPRESSED_QUEUE_CAP` | Retain for later ranking and analytical population if otherwise valid |
| UI crash before freeze | Draft remains non-authoritative | No evidence and no successful-freeze AuditEvent |
| Append succeeds but UI loses response | `UNKNOWN_PENDING_RECONCILIATION` until query resolves | Never create a new request without idempotency check |
| Audit append fails | Entire append transaction fails | No partially canonical evidence record |
| Advisory screenshot missing | Candidate remains valid if source lineage is complete | Mark artifact unavailable; never replace silently |
| Active C2 selector/release changes | Stop prospective processing | Require explicit source rebind and new operation packet |
| Future data enters trigger snapshot | `BLOCK_CHRONOLOGY_LEAKAGE` | Quarantine output and block affected build |
| Prohibited outcome feature detected | `BLOCK_PROHIBITED_DEPENDENCY` | Reject fingerprint/candidate and open QA issue |

## Candidate lifecycle

`DETECTED -> OPEN -> ACCUMULATING -> READY_FOR_REVIEW -> REVIEWED | DISMISSED | INVALID`

Additional explicit states in this matrix refine but never bypass that lifecycle. Terminal states remain immutable; later corrections create linked records.