# RPS-G4A — Pilot Discovery Supersession Record

## Disposition

`RPS-G4A` is `SUPERSEDED_FOR_PILOT_DISCOVERY`.

This disposition applies only to the first PD-WP5 operation. It does not reject or erase the need for a genuine post-activation `LIVE_PROSPECTIVE` source in a later phase.

## Historical purpose

RPS-G4A proposed a new post-activation Dukascopy source slice because the activated June binding could not satisfy the former requirement that the first PD-WP5 candidate occur after the RPS-G4 activation timestamp.

The historical proposal remains preserved:

- slice `RPS.DUKASCOPY.GBPUSD.20260728_20260801.v1`;
- interval `[2026-07-28T00:00:00Z, 2026-08-01T00:00:00Z)`;
- M1 BID/ASK and native H1 BID/ASK;
- 25 MiB compressed and 100 MiB expanded limits;
- operator-local external-artifact storage only;
- no provider request in CI.

No provider request was authorised or executed through RPS-G4A.

## Superseding amendment

`PD-G4B` proposes that the first PD-WP5 operation use the existing June source, compute run and signed TIME_GATED_REPLAY binding as a bounded `PILOT_DISCOVERY` rehearsal.

The pilot does not make the June source live, canonical or promotable. It exists to test and correct the operational system before the 2021–2023 canonical Discovery population is processed.

## Retained future-live boundary

A genuine post-activation `LIVE_PROSPECTIVE` intake and operation remain deferred to a separate future operator gate, provisionally reserved as `RPS-LIVE-G1`.

The future gate must independently define:

- exact provider request and interval;
- current-source availability;
- immutable source and compute binding;
- live chronology and first-valid rules;
- operator signing and append authority;
- QA, rollback and stop conditions.

No authority from RPS-G4A silently transfers to that future gate.

## Evidence preservation

The RPS-G4A gate packet, blocker diagnosis, tests, workflow evidence and merge receipt remain historical court records. They must not be deleted or rewritten.

## Rollback

Before PD-G4B approval, revert this supersession and restore RPS-G4A to `GATE_READY`. After a pilot has executed, preserve its records and restore future-live planning only through a new operator decision. Never relabel pilot bytes or records as LIVE_PROSPECTIVE.
