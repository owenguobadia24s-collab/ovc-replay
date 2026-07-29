# PD-JUNE-MDR-CORR1 — Corrective Evidence Assurance

## Result

Useful bounded corrective work is implemented, but the packet cannot return to `PD-JUNE-MDR-G1` because exact upstream C1 evidence and exact pre-trigger histories are unavailable.

**Packet status:** `BLOCKED_EXTERNAL_EVIDENCE_REQUIRED`

**Market-description verdict:** `NOT_ESTABLISHED`

## Resolved findings

### PD-JUNE-MDR-001 — source binding conflict

A new immutable carry-forward receipt binds the exact accepted June source bytes and replay acceptance to the already-authorised C2-v2 corrective pilot identity. The historical v1-era source-binding receipt remains unchanged. CORR1 performed no provider intake, source mutation or replay.

### PD-JUNE-MDR-002 — serialized chronology

The immutable June input contains 44 nonchronological candidate timelines, including four of six queue-promoted candidates. A read-only projection orders every candidate by `first_valid_time`, then `c2_state_id`, and aligns `source_c2_record_ids` to the same order. The corrected projection has zero chronology failures across 208 candidates.

Corrective runtime materialization now uses a chronology-safe CandidateWindow manager. Candidate-detail and queue projections defensively enforce the same chronology and fail closed on duplicate or mismatched source identities.

### PD-JUNE-MDR-005 — structural comparison completeness

All 26 reviewed units were evaluated. Exact frozen candidate-to-medoid distances were reproduced for 24 assigned fingerprints, including component distances, weights, scale features, total distance, p90 threshold and outlier state. Two units belong to `UNASSIGNED_SMALL_SAMPLE` partitions and are explicitly not applicable. Source-price joins remain complete for every reviewed timeline record.

## Remaining blockers

### PD-JUNE-MDR-003 — exact C1 claim evidence

No exact June-v2 C1 fact, level, relation or per-state formula-input bundle was supplied. Raw price bars do not independently prove the displayed C2 labels. Every semantic market-description claim therefore remains `NOT_EVALUATED`.

### PD-JUNE-MDR-004 — pre-trigger histories

Eleven reviewed units require exact pre-trigger histories for `LONG_PERSISTENCE` or `REPEATED_SWITCHING`. Those histories and evaluator input bundles were not supplied, so those trigger bases cannot be independently reconstructed.

### PD-JUNE-MDR-006 — negative controls

The immutable 208-candidate population contains no deterministic negative controls. CORR1 does not relabel or insert controls. A future control-design packet requires separate authority.

## Authority

No provider intake, replay, canonical 2021–2023 Discovery processing or append, formula/trigger/candidate/distance/clustering/threshold/model change, promotion, selector/release mutation, R2 publication, Validation consumption, probability, risk, exposure, trading, execution or agent write is authorised.

## Smallest lawful continuation

Supply hash-verifiable exact C1/level/relation/formula evidence and exact pre-trigger C2 histories for the existing June-v2 states. No market replay is required or authorised. The control-design limitation must remain open or be addressed under a separately approved packet.
