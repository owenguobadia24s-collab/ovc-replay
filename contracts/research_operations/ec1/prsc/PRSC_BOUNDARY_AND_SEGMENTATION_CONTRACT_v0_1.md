# PRSC Boundary and Segmentation Contract v0.1

## Scope

This contract governs PRSCI-WP4 boundary and segmentation challenges inside the
Research Operations PRSC namespace. It grants no C2E owner authority, no C2P,
C2.5 or C3 scientific authority, no real-source PRSC authority, and no candidate,
publication, probability, exposure or execution authority.

## Canonical-owner firewall

- Canonical C2E episode and boundary identities are immutable challenge inputs.
- A C2E internal variant is a challenger view only and cannot replace owner truth.
- A blind independent segmentation fit may read only its declared observation
  fields. Canonical C2E boundaries, episode identifiers, labels and derived owner
  markers are forbidden during fitting.
- Blind fitting and later correspondence evaluation are separate phases.

## Boundary correspondence

- Tolerance is frozen before matching as an asymmetric early/late interval.
- Tolerance cannot be widened after results are observed.
- Boundary matching is ordered, deterministic and one-to-one. A challenger
  boundary cannot confirm multiple canonical boundaries.
- Signed displacement preserves EARLY, EXACT and LATE direction.
- All unmatched canonical and challenger boundaries remain in the ledger.
- Boundary-preserving controls freeze their declared boundary positions and have
  no selection effect.

## Episode and morphology correspondence

- Episode partitions must contain non-overlapping, positive-width intervals.
- Directional correspondence preserves EXACT, PARTIAL, SPLIT, MERGE and UNMATCHED
  outcomes and accounts for unused challenger episodes.
- Morphology cores distinguish universally evaluable results from partial or
  failed views. A failed or not-evaluable view prevents a universal claim.

## Fail-closed conditions

Owner labels reachable during blind fitting, invalid or post-hoc tolerance,
partition overlap, duplicate identities, incomplete boundary accounting, or any
attempt to promote challenger output to owner truth is blocking.

## Preserved constraints

F0-A remains `HOLD`; Validation remains `LOCKED_UNCONSUMED`; CandidateFreeze
remains `NONE`; and real-source PRSC remains denied until
`PRSCI-G-EC1-CHALLENGE`.
