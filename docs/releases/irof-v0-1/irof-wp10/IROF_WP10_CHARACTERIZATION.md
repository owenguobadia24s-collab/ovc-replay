# IROF-WP10 Multi-N Performance and Capacity Characterization

Programme: `OVC-IROF-v0.1`  
Packet: `IROF-WP10`  
Gate: `IROF-G11`  
Baseline main: `1e1297b5e648ab7d553f5a418944254d7d8d22cb`  
Branch: `feat/irof-wp10-scaling-characterization`

## Ladder

The frozen synthetic ladder is `MICRO=8`, `SMALL=16`, `MEDIUM=32`, `LARGE_FIXTURE=64`. Every case uses the same scientific pack identity `IROF.WP10.SCIENTIFIC_PACK.v0_1`; N is an engineering scale only and has no scientific rank.

Exact deterministic pair-work counts are 28, 120, 496 and 2,016 respectively. This establishes `KNOWN_QUADRATIC_WORK_COUNT` for the pairwise surface without inferring a production SLA.

## Measured evidence

`benchmark.run_scaling_ladder()` measures wall time, process CPU/core-seconds, exact serialized artifact bytes, cache/no-cache work, checkpoint serialization overhead and restart recovery cost on the executing host. Required telemetry fields remain typed. Portable peak RSS is explicitly `UNAVAILABLE` rather than fabricated, and parallelism efficiency is explicitly not applicable because WP10's portable characterization runs one worker.

Exact-head tests execute the full four-case ladder and assert measurement availability, monotonic exact pair work, cache/no-cache scientific equivalence, checkpoint/restart evidence and allowed empirical-shape vocabulary. Runtime wall/CPU values are intentionally not frozen as cross-host scientific constants.

## Capacity interpretation

- Pairwise work: `KNOWN_QUADRATIC_WORK_COUNT`.
- Wall/CPU empirical shape: measured at runtime and classified only within the plan vocabulary; unstable host timing may lawfully remain `UNRESOLVED`.
- Cache path: identical scientific hash with avoided pair work after warm cache.
- Checkpoint/restart: non-negative measured operational overhead; no scientific mutation.
- Peak RSS: unavailable in this portable implementation, with reason code retained.
- Parallelism efficiency: not measured; no invented speedup claim.

## Authority delta

Synthetic performance measurement only. No scientific output, pack, method, family, selector, release, Validation state, probability, risk, exposure or execution authority changes.

## QA state

Implementation review: PASS pending exact-head automated assurance.  
Targeted/repository tests: PENDING.  
Tiered assurance: PENDING.

## Rollback

Discard the synthetic scaling fixture, benchmark harness, tests and compact characterization receipts. Scientific state is unchanged.
