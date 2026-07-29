# PD-JUNE-MDR-CORR1 Corrective Evidence Assurance Contract v0.1

## Purpose

Correct the bounded evidence and presentation failures accepted by the operator's `PD-JUNE-MDR-G1 DEFER` decision without replaying the June market window, changing source bytes, changing any formula or model, or granting semantic authority.

## Governing identity

- Programme: `OVC-PD-JUNE-2026-OPERATOR-REVIEW-AND-MARKET-DESCRIPTION-ASSURANCE.v0.1`
- Packet: `PD-JUNE-MDR-CORR1`
- Return gate: `PD-JUNE-MDR-G1`
- Pilot run: `PD.PILOT.RUN.96c16f11717e787f971851ee`
- Pilot namespace: `PD.PILOT.GBPUSD.20260622_20260625.v2`
- Source binding: `RPS.BINDING.32fb3003efa072916c11e907`
- Source slice: `RPS.DUKASCOPY.GBPUSD.20260622_20260625.v1`
- Corrective C2 release: `OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v2`
- Corrective C2 manifest: `MANIFEST.C2.OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v2.r1`
- Corrective selector: `SELECTOR.OPT-B.C2.GBPUSD.v2`

## Corrective requirements

### 1. Source-to-C2-v2 carry-forward

The historical source-binding receipt remains immutable. A separate receipt must bind the exact accepted source bytes and replay acceptance to the already-authorised C2-v2 corrective pilot identity. It must prove that CORR1 performed no provider intake, source mutation or replay.

### 2. Chronology

Candidate timeline materialization and every read-only candidate projection must order records by:

1. `first_valid_time` parsed as UTC;
2. `c2_state_id` as a deterministic tie-breaker.

The timeline and `source_c2_record_ids` must contain the same unique identities in the same chronological order. Missing timestamps, duplicate IDs or mismatched identity sets fail closed.

Historical June artifacts remain immutable. CORR1 may produce only a read-only corrected projection and a deterministic implementation for future corrective materialization.

### 3. Claim evidence

Every displayed C2 state claim requires exact references to its C1 fact values, level boundaries, relation values, formula registry and source-price observations. Missing exact C1 evidence must be reported as `NOT_EVALUATED`; it may not be inferred from price alone.

### 4. Trigger history

`LONG_PERSISTENCE` requires the exact pre-trigger C2 state history used by the frozen four-record threshold. `REPEATED_SWITCHING` requires the exact pre-trigger C2 state history used by the frozen six-record lookback and three-switch threshold. Missing history fails closed as `NOT_EVALUATED`.

### 5. Structural comparison

For each assigned reviewed fingerprint, the review projection must expose:

- exact assigned medoid;
- distance pack and scale pack identities;
- raw component distances;
- frozen domain weights and weighted contributions;
- recorded and recomputed total distance;
- p90 outlier threshold and recorded/recomputed outlier state;
- candidate dedup and overlap state.

A partition marked `UNASSIGNED_SMALL_SAMPLE` must be reported as not applicable rather than fabricated.

### 6. Controls

CORR1 must not insert, relabel or synthesize negative-control candidates into the immutable June population. Their absence remains an explicit limitation and requires a separately authorised future design if needed.

## Acceptance conditions

CORR1 can return to `PD-JUNE-MDR-G1` only when:

- the carry-forward receipt is internally consistent;
- all 208 corrected chronology projections are ordered and identity-aligned;
- materialization and review-projection tests enforce chronology;
- every reviewed assigned fingerprint has exact distance decomposition;
- all exact C1 and trigger-history evidence required by the review sample is available and bound;
- QA reports no unresolved blocking evidence gap.

If exact C1 or pre-trigger evidence is unavailable, useful corrective work must be preserved and the packet marked `BLOCKED_EXTERNAL_EVIDENCE_REQUIRED`. The market-description verdict remains `NOT_ESTABLISHED`.

## Prohibitions

This packet does not authorise provider intake, machine replay, canonical 2021–2023 Discovery processing or append, formula or trigger changes, candidate-rule changes, distance or clustering changes, threshold or model changes, semantic/family/candidate/novelty/theory promotion, selector or release mutation, R2 publication, Validation consumption, probability, risk, exposure, trading, execution or agent write.

## Rollback

Preserve all external source and pilot evidence and prior signed decisions. Revert only CORR1 code, compact derived evidence, tests, workflows, QA and programme-state records through a new non-destructive commit.
