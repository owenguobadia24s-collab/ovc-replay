# IROF Checkpoint / Restart Contract v0.1

Status: INACTIVE DETERMINISTIC RECOVERY INFRASTRUCTURE. Scientific effect: NONE.

## Core rule

Checkpoint and restart state may preserve already-completed lawful work, but it never changes the semantic run, stage contract, scientific pack, population, authority or output meaning. Attempt identity and restart count are operational lineage only.

## Completion rules

- A stage checkpoint becomes reusable only after an explicit `COMPLETE` StageCompletion record exists.
- `READY`, `RUNNING`, partial, staging and failed work cannot be represented as complete.
- A completion binds stage ID, exact StageSpec hash, output logical hash and content hash.
- Conflicting completion evidence for the same stage is quarantined and fails closed.
- Content corruption invalidates and quarantines the affected completion.
- A changed StageSpec hash invalidates reuse even if physical bytes still exist.

## Resume rules

- Resume keeps the exact same `semantic_run_id`.
- An invalid/corrupt/missing stage is rerun together with all DAG descendants that depend on it.
- Verified completed ancestors may be reused.
- A resume may never silently repair bytes or relabel incomplete output as complete.
- If a lawful affected unit cannot be recomputed, the run remains failed/quarantined rather than weakened.

## Opaque substage rule

Stage-owned internal checkpoints are opaque to generic IROF. IROF may store only owner schema identity, opaque reference, content hash, stage/run identity and attempt lineage. It must not interpret, rewrite or synthesize the stage-owned checkpoint payload.

## Determinism proof

For exact deterministic fixture stages, acceptance requires:

`fresh logical hash == repeated fresh logical hash == resumed logical hash`

Worker order, attempt IDs, restart count and checkpoint physical path are non-scientific.

## Rollback

Discard checkpoint/restart metadata and run fresh under unchanged StageSpecs and owner authority. No source programme state is modified.
