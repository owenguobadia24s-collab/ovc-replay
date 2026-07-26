# RC-G2-v0.3 — Overview and Ambient-Health Acceptance

**Decision: PASS — the deterministic Overview projection and seven-domain ambient-health contract are accepted for bounded local read-only use.**

## Accepted implementation

RC-WP2-v0.3 is accepted as a deterministic, replaceable and source-bound projection derived from the approved Research Operations read model. The accepted projection contains stable metrics, release, gate and session summaries, a consequence-aware attention inventory and the seven required health domains: Data, Read model, Artifacts, QA, Research records, Repository and Semantic.

The implementation branch was reviewed at `5301922805114a5ea6628a300095ab4b74f3cfed` and merged through PR #63 as `6701ec00469898b12f17b294610d839d4082d94b`.

## Health-truth findings

- Missing health evidence cannot be displayed as `PASS`.
- Research-record health remains `NOT_EVALUATED` with zero progress until the required schema, freeze, duplicate, cutoff and lineage assertions exist.
- Unknown explicit health vocabulary fails closed to `BLOCK`.
- Record lifecycle states are not treated as health outcomes.
- Every domain retains a human-readable consequence, affected surfaces and source references.
- Aggregate status cannot hide an individual degraded or unevaluated domain.

## Activation boundary

RC-G2 approves the Overview projection for bounded local read-only consumption by the Overview workspace. Any console adapter must verify the projection schema, represented source commit, read-model logical hash and source references before rendering. Invalid or stale input must fail closed.

The gate records authority and acceptance; the gate files do not automatically edit `Home.py` or `shell.py`, and do not silently activate a candidate file. This distinction prevents an approval record from becoming an unverified runtime switch.

The Research workspace remains fixture-only pending RC-G3. Research-record writes remain separately gated. Repository, selector, threshold, release, market, probability, exposure, execution and agent authority remain `NONE`. Remote deployment remains denied.

## Verification basis

- Canonical test run `30203088849`: PASS.
- Dedicated RC-WP2 workflow `30203088877`: PASS.
- Dedicated workflow rebuilt the candidate from the source fixture and verified the exact implementation packet.
- RC-WP2 blocking issues: `0`.

## Disposition

`RC_G2_PASS_RC_WP3_V0_3_AUTHORISED`

Next workstream: `RC-WP3-v0.3 — Research workspace, replay, evidence and queue`.
