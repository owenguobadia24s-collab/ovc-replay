# RPS-G3 — Delegated Derived Compute Acceptance Decision

- Plan: `OVC-C2-REAL-PROSPECTIVE-SOURCE-PD-WP5-ENABLEMENT-PLAN-0.1` v0.1
- Packet: `RPS-WP3`
- Gate: `RPS-G3`
- Decision: `PASS`
- Authority: `DELEGATED_AUTO_EXECUTABLE_DERIVED_LOCAL_COMPUTE`
- Baseline main: `2fbcc114d55858c95fbfefe743fb98ba5800560b`
- Compute run: `RPS.RUN.7aeb551335d766ee3bf503e6`
- Binding candidate: `RPS.BINDING.32fb3003efa072916c11e907`
- Coverage: `GAPPED`
- QA: `PASS`

## Decision

Accept the exact compact evidence for the deterministic local `TIME_GATED_REPLAY` compute and its non-activating source-binding candidate. Complete RPS-WP3 and authorise RPS-WP4 preparation within the ratified plan.

The accepted run remains derived, local, non-release and non-evidentiary for LIVE_PROSPECTIVE operation. The accepted binding status remains `ACCEPTED_FOR_REPLAY_CANDIDATE`; it is not an active research-triage binding.

## Exact accepted identities

- source slice: `RPS.DUKASCOPY.GBPUSD.20260622_20260625.v1`;
- source manifest SHA-256: `429b7b568b7a43d04893c1873773f0b1b567730f2d5d4122d6a1c06dd40e3e41`;
- output manifest SHA-256: `3c6295badd04896a9e94b4b5a3ccb354bb51de52d5927839a86f61a40ed679ff`;
- code commit: `2fbcc114d55858c95fbfefe743fb98ba5800560b`;
- admissible cutoff: `2026-06-25T00:00:00Z`;
- C1 records: 602;
- C2 states: 1,144;
- C2 transitions: 954.

## Authority retained as denied

Provider access, source repair, forward fill, interpolation, synthesis, incomplete-parent consumption, release creation, selector mutation, R2 publication, Validation consumption, LIVE_PROSPECTIVE append, ACTIVE_RESEARCH_TRIAGE, active novelty ranking, semantic or theory promotion, probability, risk, exposure, trading, execution and agent write remain denied.

## Rationale

The proposed authority delta accepts only deterministic derived-output identities produced by the already merged RPS-WP3 command. It does not activate the binding, publish a release, mutate a selector or create write authority. The delta is therefore wholly inside the plan's auto-executable envelope.

## Rollback

Revert this bounded acceptance state and preserve the source slice, compute run directory, binding candidate and all quarantines. No external deletion, mutation, relabelling or history rewrite is authorised.

## Next packet

`RPS-WP4 — operator signing binding and TIME_GATED_REPLAY acceptance preparation`.
