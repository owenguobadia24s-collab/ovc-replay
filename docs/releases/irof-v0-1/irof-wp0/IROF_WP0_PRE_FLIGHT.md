# IROF-WP0 — Court-Record Preflight and Conformance Freeze

Programme: `OVC-IROF-v0.1`  
Packet: `IROF-WP0`  
Baseline: `07d078101daf9645dafa2dea23999f9d1d688133`  
Branch: `feat/irof-wp0-conformance`

## Decision

IROF may proceed by **conform-and-generalise**, not by importing an existing single-programme harness as the generic orchestrator. The current repository contains sufficient reusable execution primitives, typed scientific-layer adapters and Research Operations evidence machinery to implement the approved design without changing frozen market semantics.

## Court-record distinctions

**Current court-record implementation:** OPT-A source/release machinery, C1, revised C2 implementations with selector governance, OccurrenceContext v0.1, Research Operations, and the SRFD execution primitives that are already merged to main.

**Accepted but inactive capability:** C2E v0.2 shadow-only package; SFC SRI/comparability/FDI/FamilyEvidenceStream conformance machinery; SFC replay capability; MCARB auxiliary/context capability where separately governed.

**Historical/superseded:** draft/unmerged FSR PR #418 and legacy/superseded C2 paths when not the pinned implementation identity of a registered stage. These are evidence/reference only and are not generic runtime dependencies.

**Future reserved:** C2P, revised C2.5, forward C3 typed AST, OPT-C, OPT-D and any new instrument/market/clock/side. They remain unregistered and fail closed.

## Reuse/refactor freeze

1. `src/ovc/opt_b/srfd/orchestration.py`: generalise checkpoint/run identity concepts; do not carry fixture-only authority constants into IROF.
2. `src/ovc/opt_b/srfd/scheduler.py`: generalise resource-contract/topological/capacity semantics while preserving the prohibition on scientific scope changes for capacity reasons.
3. `src/ovc/opt_b/srfd/semantic_cache.py`: generalise semantic-key/hash/quarantine/tile-ledger behaviour.
4. `src/ovc/opt_b/srfd/capacity_v2.py`: reuse measurement patterns and the separation of semantic identity from hostname/path.
5. `src/ovc/opt_b/sfc/replay.py`: use as replay/equivalence evidence, not as the generic engine.
6. `src/ovc/research_operations/qa.py` and `catalogue.py`: reuse directly where their contracts already fit; IROF adapters must not duplicate QA/catalogue semantics.
7. `src/ovc/context/occurrence_context/`: adapt through explicit projections only. Whole-envelope/undeclared field consumption remains forbidden.
8. SFC `representation.py`, `comparison.py`, `fdi.py`, `evidence.py`: stage adapters call typed lawful functions; IROF never reimplements their market semantics.
9. PR #418 full-stack rehearsal: DO NOT IMPORT/MERGE. Only re-express useful adversarial fixture ideas under the IROF contracts.

## Current real-data authority freeze

IROF-G0 granted engineering and synthetic execution authority only. It did not grant a real integrated June run.

Current main additionally records that the separately governed SRFD v0.6 June token is **consumed/not reusable** and the owning SRFD programme is blocked after an execution-infrastructure timeout. Any IROF restart/cache mechanism must treat consumed authority as non-renewable and must not turn an execution retry into a new run grant.

C2E real-source replay remains separately governed, with no active C2E or active empirical boundary pack. Validation is locked/unconsumed. No selector, representation, comparison, distance, family, semantic, publication, probability, risk, exposure or execution authority is created here.

## Canonical vocabulary freeze

Execution states: `READY`, `RUNNING`, `REUSED`, `COMPLETE`, `CAPACITY_EXCEEDED`, `FAILED`, `QUARANTINED`, `DEFERRED_BY_OPERATOR`, `NOT_AUTHORISED`.

Artifact states: `STAGING`, `COMPLETE`, `QUARANTINED`, `SUPERSEDED`.

Programme states remain the existing OVC programme-state vocabulary. IROF code must not introduce synonyms for these concepts unless a separately versioned contract explicitly requires them.

## Typed chain freeze

The current conformance chain preserved by SFC is:

`C2EStreamEnvelope -> RepresentationPopulation -> RepresentationPack -> RepresentationRecord/Bundle -> ComparabilityDecision -> ComparisonSpec/PairRecord/Surface -> FamilyMethodSpec -> FamilyCatalog/FamilyRecord/Assignment -> FamilyCorrespondence/InvariantCore/MetricRecord -> FamilyEvidenceStream`.

IROF may schedule these nodes and preserve their typed outputs; it may not alter the sequence requirements that are scientific-contract requirements, such as comparability-before-distance.

## WP0 acceptance

- required implementation/capability classes are explicitly distinguished;
- every currently relevant layer has an authority owner and execution disposition;
- reusable orchestration primitives have a REUSE/GENERALIZE/ADAPT/DO_NOT_IMPORT disposition;
- future layers are reserved/unregistered;
- current real-data denials and consumed-token state are explicit;
- canonical execution/artifact vocabulary is frozen;
- no code or scientific semantics changed.

Rollback: remove only the WP0 inventory/preflight/state packet. No runtime behaviour changes in WP0.
