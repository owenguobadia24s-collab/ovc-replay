# RO4 and Pattern Discovery Isolation and Trace Contract v0.1

Status: `PROPOSED_AT_RO4_G0`

Plan: `OVC-RESEARCH-OPERATIONS-FOUNDATION-v0.4-C2-STATE-SEQUENCE-EVIDENCE-IMPLEMENTATION-PLAN-0.2`

RO4 sequences use `RO4.SEQUENCE.*`. Pattern Discovery candidates use `PD.CANDIDATE.*`. The populations, review batches, answer keys, ledgers, rankings and evidence bridges are separate.

A `TRIGGER_BOUND` RO4 sequence may retain only `pd_trigger_id`, `pd_run_id` and `trigger_first_valid_at` for exact provenance. PD novelty, fingerprint, medoid, cluster, queue, review, answer key, candidate score and promotion fields are denied.

Time overlap does not create deduplication or shared identity. No RO4 sequence enters the PD evidence bridge. No PD candidate/review becomes an RO4 annotation or friction record. Any future integration requires `OVC_RO4_PD_INTEGRATION_IMPLEMENTATION_PLAN` and an operator-required design gate.
