# RO-G0 — Foundation Preflight

## Disposition

`PASS — RO-WP1 AUTHORISED AFTER MERGE`

## Exact baseline

- Repository: `owenguobadia24s-collab/ovc-replay`
- Branch: `main`
- Commit: `fefac25f19a836898c3a22228036cd66617dca07`
- Open pull requests at preflight: `0`
- Preflight test evidence: workflow run `30184455698`, conclusion `success`

RO-G0 deliberately pins the current integrated baseline rather than the provisional A2-G1-era baseline written before later OPT-A and C1 work completed.

## Upstream state reviewed

- OPT-A v2 selector set is active through A2-G5.
- Discovery is `ACTIVE_DISCOVERY`.
- Development is `ACTIVE_DEVELOPMENT`.
- Validation identity is active but consumption remains `LOCKED_UNCONSUMED`.
- OPT-B.C1 v2 WP2 passed and WP3 fixture-engine work is authorised.
- C1 market replay, release, publication and selector authority remain absent.
- C2 and later model layers remain inactive.
- Historical ABCD runtime remains quarantined.

## Plan ratification

The source implementation plan is bound by:

```text
filename: OVC_Research_Operations_Foundation_v0_1_Implementation_Plan.docx
sha256: 4f0de710ab0157041f57ab781c9411a68aaf211b3b4a41f249978f07b0d580a0
size_bytes: 193991
```

The repository control copy is `docs/plans/research_operations/OVC_RESEARCH_OPERATIONS_FOUNDATION_IMPLEMENTATION_PLAN_v0_1.md`.

## Frozen foundation boundaries

RO-G0 freezes:

1. the `ovc.research_operations` namespace beneath the existing `ovc` package;
2. Research Operations contract, schema, registry, fixture, record, documentation, application and derived-runtime roots;
3. one-way read authority from approved OPT-A and optional approved C1/C2 objects into Research Operations;
4. a hard denylist covering legacy runtime parentage, post-cutoff leakage, validation payloads, R2 writes, selectors, thresholds, agents and E-H;
5. Git/local/R2 and derived-index storage boundaries;
6. the three-workstream order and RO-G1/RO-G2/RO-G3 predecessor gates.

No implementation package or console is created by RO-G0.

## Validation and stop rules

RO-WP1 must stop if any proposed path creates a new top-level Python package, permits frozen evidence mutation or deletion, permits direct main-branch writes, reads validation payloads, reads future information in a prospective record, imports quarantined runtime code, writes raw market data or derived databases into Git, or activates market, probability, exposure, execution or agent authority.

## Authority delta

After this packet merges, only `RO-WP1 — Evidence envelope and record schemas` may begin.

RO-WP2 remains blocked pending RO-G1. RO-WP3 remains blocked pending RO-G2.

Research Operations remains `APPROVED_FOR_BUILD` only. `ACTIVE_RESEARCH`, market, probability, exposure, execution and agent authority remain `NONE`.
