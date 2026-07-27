# C2 Pattern Discovery Evidence Bridge Authority Contract v0.2

## Boundary

The Streamlit UI never edits an evidence ledger and never receives raw signing-key material. It submits a canonical `AppendRequest` to a separate local-loopback evidence service. Evidence append authority remains the existing accepted C2 prospective-evidence authority; this bridge adds no new market, semantic or exposure authority.

## Append flow

`UI form -> AppendRequest -> identity/authority validation -> nonce/sequence validation -> source/cutoff validation -> canonical serialization -> operator signature -> atomic evidence + AuditEvent commit -> result`

## AppendRequest fields

- `append_request_id`
- `operator_id`
- `session_id`
- `nonce`
- `expected_sequence_number`
- `candidate_window_id`
- `candidate_fingerprint_hash`
- `source_release_ids`
- `source_record_ids`
- `admissible_cutoff`
- `record_class`
- `record_body_hash`
- `requested_at`
- `ui_build_hash`

The request ID is globally unique and idempotent. Resubmission returns the existing result.

## Permitted evidence classes

- `STATE_FIDELITY_REVIEW`
- `BOUNDARY_CONFLICT_CASE`
- `ANOMALY`
- `INCIDENT`
- `BOUNDED_RESEARCH_QUESTION`

The service resolves all immutable source identities. Manual canonical ID entry is prohibited.

## Signing

- Ed25519 operator key.
- Private key outside Git and preferably protected by the operating-system credential facility.
- Public key registered in the operator registry.
- Signing occurs only after all validation passes.
- Streamlit does not receive or persist the raw private key.
- Single-operator signing is allowed only while the operation is local, sole-operator, descriptive and non-exposure-authoritative.

Reassessment is mandatory if a second writer is added, evidence supports C2E/C3 promotion or external claims, the service becomes remote, an agent receives proposal/write capability, capital/partner/client/regulatory use begins, or evidence and promotion approval must be separated.

## Session protections

- Bind to loopback by default.
- No default network exposure.
- Per-launch random session token.
- CSRF protection.
- Inactivity expiry.
- Explicit freeze confirmation.
- No append from fixture, `TIME_GATED_REPLAY` research-development output or `NON_EVIDENTIARY_CANDIDATE_REPLAY` mode unless the target contract explicitly permits that non-prospective record class.

## Audit chain

Every audit event records:

`event_id | previous_event_hash | sequence_number | operator_id | action | object_id | request_hash | result | timestamp | service_build_hash | event_hash | signature`

Evidence and its corresponding AuditEvent commit atomically. If atomic commitment cannot be guaranteed, neither is canonical.

## Request lifecycle

`REQUEST_CREATED -> VALIDATING -> COMMITTED | REJECTED | UNKNOWN_PENDING_RECONCILIATION -> INCIDENT`

The UI never infers success from submission alone and must query request status before retry.

## Reconciliation

- Check status immediately after submission.
- Reconcile every 30 seconds for up to 5 minutes.
- After 5 minutes, display `UNKNOWN_PENDING_RECONCILIATION`.
- Prevent the same evidence body from being submitted under a new request ID.
- Create or offer an Incident record.
- On service startup, reconcile all unresolved requests before accepting new writes.

## Fail-closed conditions

Reject or block on unknown operator, invalid session, duplicate nonce, unexpected sequence, unresolved selector/release, missing source lineage, inadmissible cutoff, candidate/fingerprint mismatch, prohibited historical seed, audit-chain mismatch, invalid signature, fixture/replay contamination or any probability/exposure/trading/execution field.

## Rollback

Disabling the bridge removes write capability but preserves committed evidence, audit events, rejected requests and incidents. No rollback rewrites or deletes canonical evidence.