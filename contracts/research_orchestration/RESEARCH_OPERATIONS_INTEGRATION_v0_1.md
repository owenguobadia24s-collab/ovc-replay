# IROF Research Operations Integration Contract v0.1

Status: APPEND-ONLY / READ-ONLY EVIDENCE INTEGRATION. Authority effect: NONE beyond existing Research Operations evidence authority.

## Purpose

IROF execution artifacts and receipts are evidence objects, not market facts. This contract maps them into the existing Research Operations artifact catalogue, non-mutating QA runner and replaceable deterministic read model without creating a second evidence authority.

## Artifact mapping

- `ArtifactRef` remains the IROF source identity.
- Research Operations catalogue declarations preserve artifact ID, owner stage, run identity, content hash, size, media/schema identity, authority classification and parent dependencies.
- Local artifacts must use approved portable `{root_alias, relative_path}` locations; absolute/unapproved paths are rejected.
- R2/GitHub Actions declarations remain remote evidence and retain explicit verification/availability state.
- Catalogue verification re-hashes local bytes and blocks missing/hash-mismatched dependencies.
- Large generated artifacts remain external; only compact declarations/receipts enter Git.

## Receipt and read-model projection

Stage and integrated run receipts are projected as `DERIVED_EXECUTION_EVIDENCE_ONLY` records. Run projection preserves canonical DAG hash/order/edges, stage statuses, telemetry, aggregate metrics and attempt lineage inside the read-model lineage payload. The read model remains derived, replaceable and non-authoritative.

## QA

IROF invokes the existing Research Operations `QARunner`. Its before/after canonical target hash check remains authoritative for non-mutation. IROF must not suppress BLOCK/QUARANTINE assertions or translate QA into scientific promotion.

## Incidents versus scientific results

Authority failures, dependency failures, corruption and capacity/execution failures may create execution incidents with `market_claim_effect=NONE`. Scientific null/negative states including `NO_STABLE_FAMILY`, `NULL_RESULT`, `NOT_ESTABLISHED`, `NOT_EVALUABLE`, `UNRESOLVED`, `ZERO_FAMILY` and residual-only outcomes remain scientific result records, not incidents.

## Determinism

The same catalogue, compact receipts, QA runs, source commit, DAG and telemetry rebuild to the same Research Operations read-model logical hash. Physical placement and UI presentation do not change evidence identity.

## Rollback

Remove the IROF read projection/integration adapter. Underlying IROF run artifacts and existing Research Operations evidence remain addressable and unchanged.
