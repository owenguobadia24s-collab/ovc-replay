# OVC C2E Neutral Episode Contract v0.1

## Authority

Active under `C2E-G0.OPERATOR.PASS.20260803T125100+0100` for deterministic implementation and shadow evidence only. C2E remains inactive, non-canonical and non-promotable.

## Object

A neutral episode groups accepted C2 states and transitions into an event-relative interval. It must retain source release, instrument, side, scope, deterministic `episode_id`, start transition and first-valid time, ordered state/transition IDs, fixed-clock membership, parent identities and changes, termination, censoring, overlap-variant membership, sensitivity, source hashes and algorithm version.

Every record carries `NEUTRAL`, `NON_SEMANTIC`, `NON_PREDICTIVE`, `NON_PROMOTABLE`, `SHADOW_ONLY`.

## Boundary inputs

Lawful inputs are transition first-valid times, axis changes/evaluability, reset/censoring records, parent changes and fixed discontinuities. The four MTA-supported markers may be retained as trace references only. Future prices, returns, operator labels, semantic names, post-hoc thresholds and cluster choices selected for coherence are prohibited.

## Frozen variants

- `STRICT`: an episode terminates at every reset, censoring boundary or non-contiguous accepted transition.
- `PRIMARY`: strict boundaries plus deterministic segmentation after a 15-minute adjacency break in accepted transition activity.
- `PERMISSIVE`: strict boundaries plus deterministic segmentation after a 60-minute adjacency break.

The variants are sensitivity views. The primary rule is preregistered and may not be replaced by observed results.

## Identity

`episode_id = sha256(source_release_id | side | scope | variant | start_transition_id | end_transition_id | algorithm_version)`. Identity collisions fail closed.

## RO4 separation

RO4 windows, candidates and friction records remain separate typed objects. Cross-references do not imply agreement or promotion. Contradictions create `CROSS_PROGRAMME_INCONSISTENCY`.

## Capacity and final gate

Each packet is bounded to four hours and 10GB, with 30-minute checkpoints. `C2E-G6` is operator-required before any activation or release plan.
