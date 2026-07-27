# Prospective Source Binding Contract v0.1

A `ProspectiveSourceBinding` joins one immutable prospective source slice, one deterministic compute run and the existing frozen OPT-A/C1/C2 model authority. It does not alter any release or selector.

## Required groups

- Identity: binding ID, schema version, research line, status and optional predecessor.
- Model authority: exact OPT-A contracts, C1 release/manifest and C2 release/manifest plus registry and parameter hashes.
- Source authority: slice ID, manifest hash, source-object IDs, instrument, sides, clocks and coverage.
- Compute authority: code commit, engine versions, run-manifest hash and output-manifest hashes.
- Chronology: eligible-data-through, run start/end and nullable active-triage start.
- QA: gap state, reconciliation, deterministic replay, lineage completeness and incidents.
- Prohibitions: release/selector eligibility `NONE`, R2 and Validation `DENIED`, exposure `NONE`.

## Chronology

`TIME_GATED_REPLAY` is non-evidentiary and cannot increment prospective counts. `LIVE_PROSPECTIVE` is invalid unless the market window, trigger and review are after an operator-pinned active-triage start and no future source object is mounted or queryable.
