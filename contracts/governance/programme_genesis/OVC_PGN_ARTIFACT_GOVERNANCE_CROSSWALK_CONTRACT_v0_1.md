# OVC PGN Artifact-Governance Crosswalk Contract v0.1

## Identity

- Programme: `OVC-PG-NATIVE-PORTFOLIO-v0.2`
- Plan: `OVC-PGN-IMPLEMENTATION-PLAN-0.2-REVISED`
- Amendment decision: `PGN-G3-R3.OPERATOR.ADJUST_SCOPE.20260805T152000+0100`
- Applies to: `PGN-G3-R1` through `PGN-G3-R6`
- Authority effect: `NONE`

## Purpose

Before any legacy candidate can proceed to native adoption at `PGN-G3`, materialise a source-backed crosswalk connecting the candidate programme to relevant subordinate or historical artifacts. The crosswalk distinguishes programme identity from release roots, plans, amendments, immutable release identities, gate and decision collections, historical evidence roots and lineage records.

## Required relationship fields

Every relationship records:

- `artifact_id`;
- `governing_programme_id`;
- `relationship_type`;
- `direction`;
- `evidence_status`;
- exact evidence paths and hashes;
- ambiguity or competing-owner findings;
- `authority_effect=NONE`.

Allowed evidence statuses are:

- `SOURCE_EXPLICIT`;
- `LINEAGE_EXPLICIT`;
- `PATH_AND_CONTENT_CORROBORATED`;
- `CANDIDATE_RELATION`;
- `UNRESOLVED`.

Allowed relationship types are:

- `EVIDENCE_ROOT_OF`;
- `PLAN_GOVERNED_BY`;
- `RELEASE_PRODUCED_BY`;
- `GATE_PACKET_OF`;
- `DECISION_RECORD_OF`;
- `HISTORICAL_EVIDENCE_OF`;
- `LINEAGE_RECORD_OF`;
- `REFERENCES`;
- `CONSUMES`;
- `UNRESOLVED_RELATION`.

## Evidence rules

1. `SOURCE_EXPLICIT` requires a source that directly names both the programme and the artifact or relationship.
2. `LINEAGE_EXPLICIT` requires an accepted lineage ledger or operator decision.
3. `PATH_AND_CONTENT_CORROBORATED` requires path alignment plus content that directly names the programme, but does not make the repository directory itself an authority source.
4. `CANDIDATE_RELATION` remains advisory and cannot satisfy a hard prerequisite.
5. `UNRESOLVED` preserves ambiguity and must not be silently converted into ownership.
6. Evidence paths carry a Git blob SHA or immutable SHA-256 where available.
7. A release root may contain evidence for more than one programme; the crosswalk must state that ambiguity rather than assign the whole root exclusively.

## Review sequencing

- Existing `PGN-G3-R1` and `PGN-G3-R2` acknowledgement receipts remain valid acknowledgements only.
- Retrospective supplemental crosswalk packets are required for their six candidates before native adoption.
- `PGN-G3-R3` must include its three-candidate crosswalk before acknowledgement.
- `PGN-G3-R4` through `PGN-G3-R6` must include equivalent crosswalks before their acknowledgements.
- No later group may be disclosed before the prior acknowledgement receipt is merged.

## Authority separation

This contract does not:

- adopt a native programme;
- accept cross-programme hard dependencies;
- establish constitutional parentage;
- grant authority inheritance;
- activate a selector, model, release, route or deferred capability;
- close migration warnings;
- grant Validation, publication, agent, probability, risk, exposure, trading or execution authority.

Programme-to-programme edge adoption remains reserved for `PGN-G5`. Native adoption remains reserved for per-programme decisions at `PGN-G3`.

## Completion condition

A review group is crosswalk-complete only when every disclosed candidate has a schema-valid record, every relationship carries exact evidence references, candidate or unresolved relations remain visibly non-authoritative, and QA confirms `authority_effect=NONE`.

## Rollback

Preserve all prior receipts and source records. Supersede an incorrect crosswalk through an append-only replacement; do not edit source history to fit the crosswalk and do not disclose the next review group while the current crosswalk is incomplete.
