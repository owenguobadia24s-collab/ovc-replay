# OPT-B.C1 v2 B1-G3 — Candidate release

**Decision: PASS — existing exact candidate releases reconciled.**

The original C1 implementation sequence materialized the B1-G3 evidence requirements across WP4, B1-G1 and WP4F before the formal `B1-G3` gate label was added to the repository court record. Discovery and Development were replayed from the exact active OPT-A v2 parents, verified for cardinality and deterministic identity, frozen under immutable release and manifest identities, and subsequently published and remotely verified by WP5.

This decision records that completed candidate-release gate without rebuilding or substituting any bytes and without regressing the repository from its later publication state.

## Accepted candidate releases

| Role | Release | Records | Record files | Manifest SHA-256 |
|---|---|---:|---:|---|
| Discovery | `OPT-B.C1.GBPUSD.DISCOVERY.2021_2023.v1` | 159,892 | 144 | `6abd6d1fb74e7f3797e9add2435eaa5e487b612efd2f4b5f4f4c59679820d5d2` |
| Development | `OPT-B.C1.GBPUSD.DEVELOPMENT.2024.v1` | 52,872 | 48 | `ca83f2d9d948be426f3d80ebc91cc981f92546dfdd07268d71938d618c51f017` |

Totals: **212,764 records**, **192 record files**, **36,170,710 verified payload bytes**, and **zero duplicate record IDs**.

## Authority retained

- Both releases remain `CANDIDATE`.
- C1 selectors remain `NONE`.
- Validation remains `LOCKED_UNCONSUMED`.
- C2 consumption remains denied pending a separate handoff review.
- No probability, exposure, trading or execution authority is granted.
- Existing WP5 remote publication evidence remains valid and is not repeated.

## Sequence reconciliation

The plan-level sequence is B1-G3 Candidate release, B1-G4 Publication, then B1-G5 Shadow activation. Repository execution used finer packets: WP4 replay, B1-G1 candidate inventory review, WP4F durable freeze, B1-G2 publication readiness and WP5 publication. This gate maps those completed packets back to B1-G3 while preserving the later B1-G4 result.

**Next authority-changing gate:** B1-G5 Shadow activation, subject to a separate operator-approved selector and C2-handoff packet.
