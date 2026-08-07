# MG C2E Neutral Episode, Phase and Binding Ledger Contract v0.1

**Contract ID:** `MG-C2E-LEDGER-0.1`  
**Programme:** `OVC-C2E-C2G-C2P-MARKET-GRAMMAR-REMEDIATION-v0.1`  
**Packet:** `MG-WP2`  
**Authority:** inactive, noncanonical `SHADOW_EXPERIMENT` computation only

## 1. Purpose

Organise already-produced C2 records into deterministic neutral episodes, per-record phases, interruptions, completions, censoring records and typed episode bindings. C2E does not replace fixed clocks, name patterns, infer outcomes or create candidate, family, grammar, semantic, probability or exposure authority.

## 2. Input boundary

The builder accepts only exact-scope C2 records with immutable source release, record and SHA-256 identities; instrument, side, clock and evaluation-scope identity; first-valid time; neutral state and transition keys; parent record binding; and computability, reset and censoring evidence.

One ledger contains one source release, instrument, side, scope and clock. Inputs are canonically ordered by first-valid time and record ID. Duplicate record IDs or first-valid times fail closed. Every input must be at or before the declared build cutoff.

C2G family, cluster, medoid, distance, variant and sensitivity fields are prohibited. Future path, outcome, return, MFE/MAE, probability, trade, semantic, grammar and parse fields are prohibited.

## 3. Boundary policy

`MG-C2E-BOUNDARY-v0.1` is deterministic and threshold-free:

1. The first evaluable record starts an episode.
2. A non-evaluable, stale, censored, conflicted or quarantined record closes any active episode as `CENSORED`, records the computability state and reason separately, and never infers continuity.
3. An explicit reset closes the active episode as `CENSORED` before the reset record.
4. A parent-record change closes the prior episode as `INTERRUPTED` and starts a new one.
5. Interruption transitions become explicit `INTERRUPTION` phases but do not themselves invent a terminal boundary.
6. Completion or termination transitions are included in the episode and close it as `COMPLETED`.
7. An evaluable episode still open at the cutoff closes as `OPEN_AT_CUTOFF`.

No outcome, family coherence or post-hoc distance may alter these rules.

## 4. Identity

Episode, phase, ledger and binding IDs are SHA-256 identities over canonical UTF-8 JSON. Identity includes the policy version, exact scope, ordered source record IDs, their SHA-256 identities, chronology and boundary disposition. It excludes local paths, machine names, run time and iteration order.

## 5. Phases and interruption

Every episode member has one phase record with an ordinal, first-valid time, source record ID, state key, transition key and parent binding. Phase kinds are `START`, `STATE`, `TRANSITION`, `INTERRUPTION`, `PARENT_CHANGE` and `COMPLETION`.

## 6. Ambiguity and non-evaluability

`NOT_EVALUATED`, `NOT_EVALUABLE`, `STALE`, `CENSORED`, `CONFLICT` and `QUARANTINED` are explicit records with required reasons. `CONFLICT` is the explicit ambiguity state; it must never be converted to neutrality or omitted.

## 7. Nesting and object binding

Typed bindings may be `NESTED_WITHIN`, `CONTEXT_PARENT` or `DERIVED_FROM`. Bindings reference existing episode IDs; preserve first-valid chronology and interval containment for contextual/nested bindings; prohibit self-parentage, cycles and unknown episodes; prohibit cross-release, cross-instrument and cross-side parentage; and may connect different clocks only through an explicit binding record.

No hidden best parent or fallback is selected.

## 8. Authority and prohibitions

MG-WP2 authorises only contracts, schemas, registries, fixtures, deterministic code, tests, QA and inactive shadow ledgers. It does not authorise C2G input, a canonical episode definition, family or grammar promotion, C3 handoff, publication, Validation, probability, risk, exposure or execution.

## 9. Acceptance

MG-WP2 passes only when the same lawful C2 inputs and policy produce byte-equivalent logical ledgers and IDs; unordered input iteration cannot change output; future records, outcomes and C2G fields are rejected; resets, parent changes, interruption, completion, censoring, conflict and not-evaluable cases are explicit; typed nesting is chronological and acyclic; schemas, registries, fixtures, focused tests and the complete repository suite pass; and QA records no reserved authority delta.

## 10. Rollback

Remove or supersede the inactive builder while preserving this contract, schemas, registries, fixtures, QA and decision evidence. Never repair a gap by inferred continuity or relabel historical C2 records in place.
