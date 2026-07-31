# RO4 Full-Corpus Performance and Sampling Contract v0.1

Status: `PROPOSED_AT_RO4_G0`

Plan: `OVC-RESEARCH-OPERATIONS-FOUNDATION-v0.4-C2-STATE-SEQUENCE-EVIDENCE-IMPLEMENTATION-PLAN-0.2`

RO4 benchmarks the exact current C2 inventory and declares machine, OS, Python, memory, storage, source counts, runtime, peak RSS and logical hashes.

Soft targets on the declared reference machine:
- active Discovery state/transition index: <=10 minutes and peak RSS <=8 GiB;
- enabled sequence generation: <=15 minutes;
- one-partition incremental update: <=90 seconds with unchanged hashes preserved;
- existing sequence lookup p95 <=2 seconds;
- window cap: <=100,000 per role/clock/side/calendar partition.

Correctness, inventory reconciliation and determinism cannot be weakened for timing. Missing benchmark evidence blocks RO4-G1. A target miss may only be `WARN_PERFORMANCE_TARGET` when correctness, full inventory and ordinary usability remain intact.

When the window cap is exceeded, ordinary materialisation stops. `DECLARED_SAMPLE_MODE` uses SHA-256(sequence_id + sampling_policy_id + sampling_version), lowest-hash selection within frozen role/clock/side/partition/boundary-source strata and exact included/excluded counts. Sampled evidence is `SAMPLED_NON_CANONICAL_EXPLORATORY`, cannot silently replace full population and cannot alone satisfy C2E design opening.
