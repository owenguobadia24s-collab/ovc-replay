# GRT v0.2 / VIT DebtFloor Integration Ownership Contract v0.1

**Programme:** `OVC-GRT-V0.2-REPOSITORY-CONSTITUTION-CONTINUOUS-CONFORMANCE`  
**Packet:** `GRT2-VIT-DEBTFLOOR-INTEGRATION-OWNERSHIP-REMEDIATION`  
**Authority effect:** `NONE_INTEGRATION_MECHANICS_CORRECTION`

## 1. Purpose

This contract removes the active GRT DebtFloor singleton registry from ordinary
programme packet payloads without weakening GRT law. The actionable inherited
debt set remains monotonic and `NO_NEW_HYGIENE_DEBT == 0` remains mandatory.
The exact next floor is owned by GRT and projected by `GRT-EXACT` over the exact
VIT prospective tree. The single serialized VIT/SIQ physical materialisation
transaction makes that projection effective.

## 2. Historical anchors

The repository versions `GRT_DEBT_FLOOR_G0.json`, `GRT_DEBT_FLOOR_G1.json`,
`GRT_DEBT_FLOOR_G2.json` and the G2 current-pointer bytes remain immutable
historical anchors. This packet does not rewrite, delete, replace or reinterpret
them.

The migration anchor is:

- generation: `2`
- floor hash: `cc79b13935e91775165d10903126cb7909a0ec78eeb6ddd7d6692e36a7e8bedb`
- constitution hash: `cac9fc5f0e31db08c4c37153c92a214fcc482414421f34d74c594faec65a71b0`

## 3. Ownership boundary

### 3.1 Ordinary packet responsibility

An ordinary programme packet SHALL provide its stable logical PIP, source-bound
authority and dependency frontier, tests, QA and completion intent. It SHALL NOT:

- modify `registries/governance/grt_v0_2/GRT_DEBT_FLOOR_CURRENT.json`;
- add or modify `registries/governance/grt_v0_2/debt_floors/GRT_DEBT_FLOOR_G<n>.json`;
- include either surface in PIP logical changes;
- rebuild or re-identify its PIP merely because the physical DebtFloor
  generation advanced; or
- merge current `main` into the logical packet branch to acquire a new floor.

### 3.2 GRT responsibility

`GRT-EXACT` SHALL evaluate the exact physical predecessor and exact qualified
prospective result tree. It SHALL fail closed on new/recurrent actionable debt,
debt expansion, material debt change, non-evaluability, adapter error, policy
mutation or packet-owned floor mutation.

For a passing candidate it SHALL emit one deterministic virtual DebtFloor whose
identity binds:

- floor-policy identity;
- next physical-main generation ordinal;
- exact predecessor commit and tree;
- exact prospective result tree;
- constitution identity; and
- complete ordered actionable grandfathered finding set.

Source branch, PR number, worker, commit message, author, timestamps and
incidental source-head commit identity are not floor identity.

### 3.3 VIT/SIQ responsibility

`DSAI_VIT_PHYSICAL_CONTROLLER`, through
`DSAI_SIQ_EXISTING_SERIALIZED_GATEWAY`, remains the single physical writer. It
may materialise only the exact tree carrying the passing proof. Exact
post-materialisation tree equality is mandatory. Placement-only main movement
recomputes A1/A2 placement and GRT proof only; it does not rebuild A0/PIP.

## 4. Generation and continuity

The first physical main commit carrying the exact active policy is virtual floor
generation 3. Each subsequent first-parent physical main generation advances
the virtual floor by one. Recomputing a physical commit's floor from its first
parent, result tree and finding set MUST reproduce the same hash that was
projected before that commit materialised.

A candidate floor is always `current physical floor generation + 1`, regardless
of the number of commits on its source branch. This preserves squash
materialisation equivalence.

## 5. Conformance invariants

A conforming implementation MUST preserve all of the following:

1. `NO_NEW_HYGIENE_DEBT == 0`.
2. Candidate actionable IDs are a subset of the current actionable IDs plus an
   exact separately authorised identity substitution.
3. No actionable debt extent expands or changes materially.
4. Resolved findings do not regain grandfathering.
5. B0 and historical G0/G1/G2 remain immutable.
6. One exact GRT proof binds one predecessor/result-tree pair.
7. One VIT/SIQ physical writer materialises one exact qualified result tree.
8. Ordinary packet PIP identity is independent of DebtFloor generation and
   physical placement.
9. Policy amendment is fail-closed and operator-required when meaning-bearing.

## 6. Required evidence

- Active policy:
  `registries/governance/grt_v0_2/GRT_DEBTFLOOR_INTEGRATION_OWNERSHIP_v0_1.json`
- Policy schema:
  `schemas/governance/grt_v0_2/grt_debt_floor_integration_ownership.schema.json`
- Projection implementation:
  `scripts/governance/grt_v0_2/integration_floor.py`
- Exact integration runner:
  `scripts/governance/grt_v0_2/grt_exact_integration_floor.py`
- No-write preparation helper:
  `scripts/governance/grt_v0_2/prepare_next_debt_floor.py`
- Regression assurance:
  `tests/governance/grt_v0_2/test_grt2_vit_debtfloor_integration_ownership.py`

## 7. Rollback

Rollback is correct-forward only. A failure may disable virtual projection for
new integrations and return to a separately authorised non-churning safer path.
It may not force-push, rewrite history, alter G0/G1/G2, weaken GRT-EXACT, permit
new debt, or silently restore ordinary-packet ownership of the singleton floor
pointer.
