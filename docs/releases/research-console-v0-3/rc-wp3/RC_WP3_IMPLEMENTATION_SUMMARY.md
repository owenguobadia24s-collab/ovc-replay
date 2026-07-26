# RC-WP3-v0.3 — Research Workspace, Replay, Evidence and Queue

**Disposition: COMPLETE — deterministic Research workspace projection candidate ready for RC-G3 review.**

## Implemented

This work package adds a source-bound and replaceable Research projection with:

- explicit instrument, release, clock, side, selected time and cutoff mode;
- the latest frozen pre-cutoff observation and linked claims;
- replay rows derived from immutable realization paths;
- evidence cards for support, contradiction, boundary, null, anomaly, censored and unresolved roles;
- queue items for due realizations, censored paths, incidents and missing sources;
- read-only session summaries;
- deterministic ordering, source references and logical SHA-256.

## Cutoff safety

PROSPECTIVE mode physically excludes records and replay points first valid after the selected cutoff. REVIEW mode may include later records, but each later item is labelled POST_CUTOFF_REVIEW. The research brief remains anchored to the latest observation frozen by the cutoff.

## Evidence and queue discipline

Evidence roles come from source records rather than card colour or position. Unknown roles fail closed to UNRESOLVED with blocking presentation status. Queue entries are derived from immutable source state and retain a consequence and source references.

## Activation boundary

The replaceable local candidate path is:

`var/research_operations/console/research_candidate.json`

The existing Home.py and shell.py remain fixture-only and do not consume this candidate. RC-G3 must separately accept the projection and a fail-closed adapter before bounded local Research consumption may begin.

Research-record creation remains separately gated. Repository, selector, threshold, release, market, probability, exposure, execution and agent authority remain NONE. Remote deployment remains denied.

## Local build

`PYTHONPATH=src python scripts/build_research_console_research.py --source fixtures/research_operations/research_console_v0_3/RC_WP3_RESEARCH_SOURCE_RECORDS.json --output var/research_operations/console/research_candidate.json --mode PROSPECTIVE`

## Next gate

RC-G3-v0.3 — Research workspace, replay, evidence and queue acceptance.
