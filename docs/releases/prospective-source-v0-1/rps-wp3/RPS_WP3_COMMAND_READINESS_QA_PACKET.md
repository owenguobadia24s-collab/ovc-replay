# RPS-WP3 — Derived Compute Command-Readiness QA

- Plan: `OVC-C2-REAL-PROSPECTIVE-SOURCE-PD-WP5-ENABLEMENT-PLAN-0.1` v0.1
- Packet: `RPS-WP3`
- Baseline main: `fe6483264f7652ede5e679140878788c15276da4`
- Prerequisite: `RPS-G2` PASS and merged
- Candidate branch: `build/rps-wp3-derived-compute-command`
- Pull request: `#107`
- Tested head: `510e6c6a0dc887d1587c0e563fe3b0b710d699bf`
- Dedicated workflow: `30290939053`, job `90060276971` — PASS
- Canonical workflow: `30290938717`, job `90060276151` — PASS
- QA recommendation: `PASS_COMMAND_READY`
- Packet state after merge: `RUNNING_AWAITING_OPERATOR_LOCAL_COMPUTE`

## Implemented

1. Exact verification of the RPS-G2 compact evidence index and local frozen source bytes.
2. Deterministic M1 parsing and UTC-aligned 15M/2H_A_L aggregation.
3. Explicit incomplete-parent outputs and exclusion from C1/C2.
4. Additive TIME_GATED_REPLAY profile for the exact C1 formula engine.
5. Additive TIME_GATED_REPLAY profile for the actual C2 structure/state engine.
6. 2H local, 15M local and 15M-with-latest-first-valid-2H-parent scopes.
7. Deterministic payload manifest, compute-run identity and non-activating source-binding candidate.
8. Local staging quarantine on failure and source non-mutation.
9. Windows preflight/execute wrapper, contract, schema, tests and dedicated CI denial.

## Expected local coverage

Per side:

- 288 total 15M parents: 271 complete, 17 unavailable;
- 36 total 2H parents: 30 complete, 6 unavailable;
- 301 C1 records per side, 602 total;
- C2 records produced only from complete C1 parents across six role/clock/side/scope streams.

Transition counts are deterministic but evidence-dependent and are recorded by the local compute receipt.

## Tests

The dedicated workflow passed:

- focused prospective compute tests;
- the complete canonical repository suite;
- an explicit assertion that external execution returns blocked in CI.

The independent canonical workflow also passed the repository-wide test suite.

Tested behaviours include:

- M1 gap creates unavailable parents without fill;
- incomplete parents cannot enter C1;
- prospective C1 profile reuses `C1.FORMULAS.v0.1`;
- historical C1 profile remains covered by canonical regressions;
- prospective C2 handoff requires exact non-release RPS identities and denied authorities;
- actual C2 engine emits deterministic state and transition outputs;
- wrong gate fails closed;
- external execution in CI fails closed;
- all prior provider, source, C1 and C2 regressions pass.

## Authority assessment

The implementation is within the approved RPS plan and RPS-G2 authority. It prepares local derived computation only. The code does not perform the actual operator-local run in GitHub, and no compute result or active binding is claimed.

The following remain denied:

- provider access;
- source mutation, repair, fill, interpolation or synthesis;
- incomplete-parent consumption;
- release or selector mutation;
- R2 publication;
- Validation consumption;
- LIVE_PROSPECTIVE append;
- ACTIVE_RESEARCH_TRIAGE;
- semantic/theory promotion;
- probability, risk, exposure, trading, execution and agent write.

## Warnings and blocker

GitHub cannot access the accepted CSV source objects under the operator's `OVC_EXTERNAL_ARTIFACT_ROOT`. Therefore it cannot execute the real compute, calculate the final `RPS.RUN.*` and `RPS.BINDING.*` identities or evaluate RPS-G3.

This is an expected external-artifact boundary, not an implementation defect.

## Rollback

Revert the bounded RPS-WP3 command implementation. Preserve the accepted RPS-G2 source, original quarantines and compact evidence. No external derived run exists until the operator executes the merged command.

## Recommendation

`PASS_COMMAND_READY` — merge the tested non-activating implementation, then stop for operator-local `preflight` and `execute`. Resume with the five compact compute files for RPS-G3 evaluation.
