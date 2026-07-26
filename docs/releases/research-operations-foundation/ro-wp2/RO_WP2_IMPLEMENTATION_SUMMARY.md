# RO-WP2 — Research CLI and Artifact Catalogue

## Result

`IMPLEMENTED — READY FOR RO-G2 OPERATOR REVIEW`

## Baseline

- Repository: `owenguobadia24s-collab/ovc-replay`
- Baseline: `51f94c55eaed8c997bc141d33f0f3f4fa452bb0f`
- Predecessor: `RO-G1 PASS`
- Validation: `LOCKED_UNCONSUMED`

## Implemented

- `ovc research`, `ovc artifact`, and `ovc queue` command families;
- environment-only local configuration and portable path aliases;
- derived draft storage under `var/research_operations/`;
- append-only frozen record storage with exclusive-write denial;
- immutable AuditEvent emission for every public write action;
- session, observation, claim, realization, adjudication, close and supersession handlers;
- approved-root traversal and symlink guards;
- deterministic local catalogue scanning and logical inventory hashes;
- compact GitHub Actions and R2 descriptor ingestion without network operations;
- changed-byte, missing-object, expired-artifact, orphan-manifest and dependency detection;
- realization, incident, session, stale-catalogue and missing-artifact queues;
- Windows launch script and operator guide;
- synthetic workflow and catalogue fixtures with executable tests.

## Authority boundary

RO-WP2 implements code and governance only. No operator research record is created by the work packet. The CLI and catalogue are not active until RO-G2 passes. RO-WP3 remains blocked pending RO-G2.
