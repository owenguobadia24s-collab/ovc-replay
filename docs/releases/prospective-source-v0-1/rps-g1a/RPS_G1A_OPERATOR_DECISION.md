# RPS-G1A — Operator Decision

- Plan: `OVC-C2-REAL-PROSPECTIVE-SOURCE-PD-WP5-ENABLEMENT-PLAN-0.1`
- Plan version: `0.1`
- Packet: `RPS-WP2`
- Gate: `RPS-G1A`
- Decision: `PASS`
- Authority: `OPERATOR`
- Approval command: `OVC APPROVE RPS-G1A`
- Approved on: `2026-07-27`
- Baseline main: `c61825aa6edc3389566e94316138391db49ac9d5`
- Approved branch head: `bf65fedcd1cf354641fa25f87f4ab5acb642cae7`
- Pull request: `#101`
- Canonical test workflow: `30281531558`
- Canonical test job: `90028842735`
- QA result: `PASS`

## Decision

Approve one exact operator-local Dukascopy GBP/USD intake using:

- slice `RPS.DUKASCOPY.GBPUSD.20260622_20260625.v1`;
- half-open interval `[2026-06-22T00:00:00Z, 2026-06-25T00:00:00Z)`;
- M1 BID, M1 ASK, native H1 BID and native H1 ASK;
- compressed-byte limit `26214400`;
- expanded-byte limit `104857600`;
- `%OVC_EXTERNAL_ARTIFACT_ROOT%` only.

This decision supersedes the unavailable July intake authority granted by RPS-G1. It does not relabel, reuse or admit any byte from the quarantined July attempt.

## Evidence

The exact June adapter profile, wrapper, deterministic identities, fake-provider fixtures, original-profile regression protection, no-network preflight and CI execution-denial checks are present on the approved branch. The canonical repository unittest workflow completed successfully on the approved branch head. No provider request occurred in CI and no real June source slice exists at decision time.

## Authority delta

Granted:

- one exact operator-local provider request for the June replacement scope;
- local immutable source-slice freeze if and only if all four streams and every integrity condition pass.

Retained as denied:

- any provider request outside the approved June scope;
- retry or acceptance of the superseded July slice identity;
- LIVE_PROSPECTIVE append;
- ACTIVE_RESEARCH_TRIAGE or live Pattern Discovery processing;
- active novelty ranking;
- selector, release or R2 mutation;
- Validation consumption;
- semantic, theory, model, family or candidate promotion;
- C2E, C2.5, C3, OPT-C or OPT-D;
- probability, risk, exposure, trading, execution or agent-write authority.

## Acceptance and failure behaviour

The local command must fail closed and quarantine without an accepted slice for any missing object, byte-limit breach, malformed transport, boundary or gap failure, duplicate or ordering failure, BID/ASK mismatch, native-H1 mismatch or overwrite attempt. No repair or substitution is authorised.

## Rollback

Before a frozen June slice exists, rollback is withdrawal of the RPS-G1A request authority and reversion of the amendment merge. Preserve the July quarantine incident and any June failure incident. After a checksum-addressed June slice freezes, preserve it and its receipts while withdrawing all downstream consumption authority.

## Next work

1. Squash-merge PR #101 into `main` after verifying the pinned head and successful required checks.
2. Pull the resulting main tip locally.
3. Run the approved June preflight and execute commands.
4. Supply only the compact manifest and six compact receipt files.
5. Resume RPS-WP2 and evaluate RPS-G2.
