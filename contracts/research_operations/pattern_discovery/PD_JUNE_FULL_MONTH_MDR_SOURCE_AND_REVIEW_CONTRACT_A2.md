# PD-JUNE-FULL-MONTH-MDR Source and Review Contract Amendment A2

## Binding and precedence

This amendment is bound to operator PASS at `PD-JUNE-FM-A2-PAIRED-SPARSE-M1-ACCEPTANCE`. It supersedes only A1 clauses requiring every non-weekend M1 minute and all 48 July context H1 hours to be present. The base contract and A1 remain in force otherwise.

## Paired sparse M1 admissibility

An absent M1 timestamp is admissible only when:

1. BID and ASK timestamp sets are exactly identical over the full source interval.
2. Both sides have zero duplicates and zero non-monotonic rows.
3. Every gap run, absent timestamp count and affected derived bucket is recorded.
4. No price or volume is interpolated, forward-filled, copied or synthesised.
5. The source is labelled `PAIRED_PROVIDER_ABSENCE_ACCEPTED_WITH_EXPLICIT_CENSORING`.

A one-sided absence, timestamp mismatch, inverted BID/ASK relation, unrecorded gap, duplicate or non-monotonic row blocks and quarantines the run.

## Derived-clock completeness

- 15M requires 15 distinct consecutive M1 timestamps.
- H1 requires 60 distinct consecutive M1 timestamps.
- 2H requires 120 distinct consecutive M1 timestamps.
- Any bucket lacking complete required membership is absent from the evaluable stream and recorded as `NOT_EVALUABLE` or `CENSORED`.
- A candidate, control or review window may not bridge an incomplete bucket or treat either side of a gap as continuous.
- Native H1 may corroborate complete M1-derived H1 but may not repair missing M1 detail.

## July context

July remains context-only. The six observed incomplete context hours are admissible as censored context:

- 2026-07-01T21:00:00Z
- 2026-07-01T22:00:00Z
- 2026-07-01T23:00:00Z
- 2026-07-02T20:00:00Z
- 2026-07-02T21:00:00Z
- 2026-07-02T22:00:00Z

Exactly 42 complete July H1 context hours per side are expected for the observed source. A future source with a different exact gap pattern requires fresh evidence and may not inherit this observation silently.

## Evidence

The manifest, provider receipt, inventory, coverage QA, BID/ASK reconciliation, H1 reconciliation and freeze receipt must record A2, the paired sparse policy, downstream censoring, no repair and retained non-release authority.

## Authority

This amendment changes source admissibility and downstream evidence completeness only. It grants no market semantic, discovery, promotion, selector, publication, Validation, probability, risk, exposure, trading, execution or agent-write authority.
