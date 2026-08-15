# RCCR Core Contract v0.1

Status: IMPLEMENTED / NON-AUTHORITATIVE
Programme: OVC-RCCR-CONFORMANCE-v0.1
Packet: RCCRI-WP1

RCCR is a permanent Research Operations synthesis register. It indexes externally owned research identity and evaluates requirement-level coverage without becoming a scientific owner.

## Binding invariants

1. The seven durable v0.1 object families are `ResearchCoverageItem`, `ResearchRequirementProfile`, `ResearchCapabilityFrontier`, `ResearchCoverageAssessment`, `CapabilityNeedAssessment`, `RCCRBootstrapManifest`, and `RCCRRefreshTrigger`.
2. Every canonical RCCR object SHALL carry `schema_version`, canonical identity, `first_valid_time` where applicable, provenance, and `authority_effect = NONE`.
3. Canonical serialization SHALL be deterministic UTF-8 JSON with recursively sorted object keys, compact separators, no NaN/Infinity, and a terminal newline only at storage time.
4. Identity SHALL derive from canonical semantic bytes after excluding the identity/hash envelope itself. Field order and JSON formatting MUST NOT alter identity.
5. Schemas SHALL be closed. Unknown mandatory enum values and unknown top-level fields fail closed.
6. Frozen records are append-only. An existing identity may not be overwritten. Supersession creates a new identity and preserves the predecessor.
7. Canonical objects SHALL NOT embed large raw payloads, secrets, arbitrary local filesystem paths, traversal paths, or owner artifacts. References are identifiers or safe repository-relative references only.
8. RCCR SHALL preserve owner authority. `AVAILABLE != AUTHORISED`, `AUTHORISED != ACTIVE`, `IMPLEMENTED != SCIENTIFICALLY_REQUIRED`, and `NEED_SUPPORTED != ACTIVATION_AUTHORITY`.
9. ResearchCoverageRegisterSnapshot is a rebuildable read model, not a durable authority-bearing family.
10. Validation 2025 payload consumption, real-source EC1 authority, Path-2 execution/preregistration, probability/risk/exposure/trading/execution and agent-write remain outside this packet.

## Persistence

The registered canonical root is `records/research_operations/rccr/v0_1/<family>/`. Writes are exclusive-create. Audit integration is append-only under `records/research_operations/rccr/v0_1/audit/` and may additionally forward an event to the existing Research Operations audit boundary.

## Rollback

Forward supersession/revert only. Never rewrite or delete historical canonical records to perform a rollback.
