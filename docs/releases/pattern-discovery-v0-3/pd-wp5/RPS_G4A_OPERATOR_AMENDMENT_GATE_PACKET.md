# RPS-G4A — Post-Activation Source Extension Operator Amendment

## Gate identity

- Gate ID: `RPS-G4A`
- Plan: `OVC-C2-REAL-PROSPECTIVE-SOURCE-PD-WP5-ENABLEMENT-PLAN-0.1`
- Plan version: `0.1`
- Blocked packet: `PD-WP5`
- Baseline main: `5842c8e9079efb82e5dc78dbeba31005c27eaa24`
- Candidate branch: `build/pd-wp5-first-live-prospective-operation`
- Decision authority: `OPERATOR`
- Allowed decisions: `PASS`, `DEFER`, `BLOCK`, `QUARANTINE`, `SUPERSEDE`

## Current authority

RPS-G4 is approved and active for:

- one bounded GBP/USD PD-WP5 operation;
- source binding `RPS.BINDING.32fb3003efa072916c11e907`;
- signing binding `RPS.SIGNING.50092c28981fef08f53a6cb5`;
- operator `OVC.OPERATOR.PRIMARY.LOCAL.V1`;
- active model `OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v1`.

ACTIVE_RESEARCH_TRIAGE is true. Candidate append remains false until a new LIVE_PROSPECTIVE candidate resolves immutable source lineage.

## Blocking evidence

- Activation merge: `aa29b23a7a83e33880ac2d80deb013f0c0390f30`
- Activation cutoff: derived from that merge's Git committer timestamp
- Active binding eligible data through: `2026-06-25T00:00:00Z`
- Required live chronology: market window and first-valid trigger strictly after activation

The active binding ends more than one month before activation. It cannot lawfully produce a post-activation candidate. Replay relabelling, synthetic extension and manual source-ID entry are prohibited.

## Proposed authority delta

A `PASS` authorises exactly one new bounded Dukascopy intake:

```yaml
slice: RPS.DUKASCOPY.GBPUSD.20260728_20260801.v1
interval: '[2026-07-28T00:00:00Z, 2026-08-01T00:00:00Z)'
streams:
  - M1 BID
  - M1 ASK
  - native H1 BID
  - native H1 ASK
limits:
  compressed: 25 MiB
  expanded: 100 MiB
provider: DUKASCOPY
instrument: GBPUSD
destination: OVC_EXTERNAL_ARTIFACT_ROOT_ONLY
```

The request may execute only after the July 2026 native-H1 monthly BI5 BID and ASK objects are available. No M1-derived H1 substitution is permitted.

After successful intake, the approved work is limited to:

1. immutable local freeze and exact source QA;
2. existing GAPPED acceptance rules only if the evidence satisfies them;
3. deterministic 15M/2H OPT-A→C1→C2 processing;
4. exact new post-activation source binding;
5. one PD-WP5 LIVE_PROSPECTIVE operation;
6. stop at PD-G5.

## Authority not granted

A `PASS` does not authorise:

- provider access before the stated H1 objects are available;
- another provider, instrument, clock, side or interval;
- reuse or relabelling of the June or quarantined July identities or bytes;
- gap filling, interpolation, repair or synthesis;
- TIME_GATED_REPLAY backfill;
- more than one PD-WP5 operation;
- automatic evidence creation or agent writes;
- active novelty ranking;
- semantic, family, archetype or theory promotion;
- C2 mutation, C2E, C2.5, C3, OPT-C or OPT-D;
- selector/release/R2 mutation;
- Validation consumption;
- probability, risk, exposure, trading or execution authority.

## Acceptance conditions

The amendment may pass only if the operator accepts:

1. the exact interval and four streams;
2. the 25 MiB compressed and 100 MiB expanded abort limits;
3. external-artifact storage only;
4. no provider request in CI;
5. no request before native H1 availability;
6. immutable new slice identity with no reuse of June or prior July bytes;
7. exact source QA and fail-closed quarantine on failure;
8. no replay relabelling;
9. one-operation PD-WP5 limit;
10. mandatory stop at PD-G5.

## Tests and QA

The candidate branch includes:

- no-network PD-WP5 preflight;
- post-activation chronology tests;
- replay-contamination tests;
- exact amendment-scope tests;
- canonical repository tests;
- QA packet `PD_WP5_BLOCKER_QA_PACKET.md`.

Final workflow IDs and candidate head are pinned after CI.

## Changed files

The gate-preparation branch contains only:

- diagnostic implementation and Windows wrapper;
- tests and CI;
- first-operation contract;
- blocker QA;
- machine-readable PD-WP5 state;
- this consolidated amendment packet.

No provider request, market data, private key, evidence ledger, cache or machine path is committed.

## Warnings

1. The exact source window is post-activation but cannot be fetched until the provider's July native-H1 monthly objects exist.
2. Provider publication timing is not guaranteed by this programme.
3. A successful source intake does not itself create a candidate or evidence record.
4. PD-WP5 remains blocked until the source, compute and new binding all pass.
5. RPS-G4 remains active but fail-closed while waiting.

## Unresolved issues

No implementation defect is known. The unresolved issue is external provider-object availability plus operator authority for the new request.

## Rollback

Before intake, rollback is a revert of the amendment decision and diagnostic branch. After intake, disable the new binding and preserve all source, compute, key, signature, incident and quarantine artifacts. Never relabel or delete prior source evidence.

## Recommended decision

`DEFER` until the July native-H1 objects are available, then `PASS` the exact bounded intake without changing scope.

A direct `PASS` now records authority but the command must still refuse provider execution until the availability condition is satisfied.

## Exact work after approval

1. record the RPS-G4A operator decision;
2. implement the exact post-activation adapter scope without provider access in CI;
3. run an operator-local availability probe;
4. if available, execute one bounded request and freeze the source;
5. accept or quarantine through exact QA;
6. process OPT-A→C1→C2 and create a new exact binding;
7. execute one PD-WP5 operation;
8. stop at PD-G5.
