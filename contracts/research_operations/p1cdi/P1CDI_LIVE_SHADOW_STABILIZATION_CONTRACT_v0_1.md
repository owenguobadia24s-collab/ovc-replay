# P1CDI Live Read-Only Shadow and Stabilization Contract v0.1

**Programme:** `OVC-P1CDI-CONFORMANCE-v0.1`  
**Packet:** `P1CDII-WP10`  
**Authority effect:** `NONE`  
**Activation boundary:** `P1CDII-G-OBSERVABILITY-ACTIVATE` (`OPERATOR_REQUIRED`)

## 1. Scope

P1CDII-WP10 may observe the exact current P1CDI source scope and exercise the already-implemented read-only projection/index machinery in **shadow only**. The shadow is evidence-generating and non-operational. It MUST NOT create operational reliance, new source intake, candidate/freeze state, scientific disposition, Validation access, publication, probability/risk/exposure/trading/execution authority, or agent-write authority.

## 2. Exact source binding

A shadow observation MUST bind:
- the exact physical-main commit and tree being observed;
- the exact `P1CDI_BOOTSTRAP_SOURCE_CENSUS_MANIFEST_v0_2.json` identity and SHA-256;
- the exact `P1CDI_BOOTSTRAP_SOURCE_COMPLETENESS_MANIFEST_v0_1.json` identity and SHA-256;
- the exact expected and reconciled source counts.

The court-record source census controls. A zero-member source scope is a valid exact scope when the census says zero; WP10 MUST NOT invent members from summaries, chat, fixtures, or adjacent programmes.

## 3. Stabilization predicates

A shadow observation is stable only when all of the following hold:
- currentness is `CURRENT`;
- expected and reconciled source counts are equal;
- no source-identity drift or owner-semantic conflict is present;
- reference and optimized read paths are exactly equivalent;
- protected-source and Validation leak counts are zero;
- candidate-authority survivor count is zero;
- index integrity is valid;
- capacity is complete without sampling or silent omission.

Observations and ledgers are deterministically content-hashed. Any integrity mismatch fails closed.

## 4. Incident routing

The following conditions require requalification and MUST NOT be silently repaired or treated as activation evidence:
`FALSE_CURRENTNESS`, `SOURCE_FRONTIER_UNRESOLVED`, `SOURCE_IDENTITY_DRIFT`,
`OWNER_SEMANTIC_CONFLICT`, `REFERENCE_OPTIMIZED_DIVERGENCE`, `MODE_LEAK`,
`VALIDATION_LEAK`, `CANDIDATE_AUTHORITY_BYPASS`, `INDEX_CORRUPTION`,
`CAPACITY_EXCEEDED`.

Incident handling is forward-only and evidence-preserving. Canonical historical records are not deleted or rewritten.

## 5. Authority firewall

`read_only_shadow=true` does not imply `operational_reliance=true`. Every WP10 observation, evaluation and stabilization ledger MUST encode `operational_reliance=false`, `automatic_activation=false`, and `authority_effect=NONE`.

Only an explicit operator PASS at `P1CDII-G-OBSERVABILITY-ACTIVATE` may permit source-scoped operational read-only P1CDI reliance. Research Console consumer admission and continuous-intake writes remain separately governed.
