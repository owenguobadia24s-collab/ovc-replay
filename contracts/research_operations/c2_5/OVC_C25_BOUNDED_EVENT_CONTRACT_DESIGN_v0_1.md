# OVC C2.5 Bounded Event-Contract Design v0.1

## Authority

Active under `C25-G0.OPERATOR.PASS.20260803T125100+0100` for draft-contract implementation and non-promotable shadow evaluation only. No rule is an event and no event authority is active.

## Bounded rules

Only `BOUNDARY_ZONE_ENTRY`, `BREACH_ACTIVE`, `LONG_PERSISTENCE`, and `REPEATED_SWITCHING` may receive draft contracts.

`RETURN_INSIDE` and `COMPRESSION_TO_DISPLACEMENT` remain deferred because the accepted population contains zero fires. `LOCAL_PARENT_CONFLICT` and `ALIGNMENT_GAINED` remain blocked because they are not evaluable in the accepted population.

## Draft-contract standard

Each draft references the existing frozen evaluator and records rule/version, exact prerequisite inputs, evaluability decision tree, first-valid timestamp, deterministic occurrence identity, start/continuation/termination, reset and censoring behaviour, duplicate suppression, strict/primary/permissive sensitivity, optional fail-closed C2E reference, source hashes, algorithm version and criterion-level evidence.

Every output carries `DRAFT_CONTRACT`, `NON_SEMANTIC`, `NON_PREDICTIVE`, `NON_PROMOTED`, `SHADOW_ONLY`. A single readiness badge, hidden score or composite rank is prohibited.

## Occurrence identity

`occurrence_id = sha256(source_release_id | rule_id | side | scope | first_valid_time | source_state_or_transition_id | contract_version)`. Repeated persistence or continued conditions cannot emit another start until the frozen condition has ceased and lawfully re-entered. Identity collisions fail closed.

## C2E dependency

Draft design may proceed from accepted C2 and MTA occurrence identities. C2E linkage is `NOT_AVAILABLE` unless an accepted versioned C2E shadow is present. Episode linkage never grants event authority.

## Capacity

Each packet is bounded to 14,400 seconds and 10,737,418,240 retained bytes, with checkpoints at least every 30 minutes. Capacity failure preserves completed shards and stops without sampling or formula/threshold changes.

## Denials and final gate

No new or reclassified rule, formula, threshold, clock, reset, selector, release, semantics, candidates, prediction, Validation, publication, probability, risk, exposure or execution. `C25-G6` is operator-required and contains four independent rule decisions before any later activation or release plan.
