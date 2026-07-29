# OVC PD June 2026 Operator Review and Market-Description Assurance Plan v0.1

## 1. Operator directive

The operator directs OVC to continue from current lawful `main` while explicitly **not** advancing to a 2021–2023 canonical Discovery run. The immediate purpose is to inspect the June 22–25, 2026 Pilot Discovery operator-review results, identify workflow and evidence defects, define improvements, and determine whether current evidence establishes that the system consistently and reliably describes the market.

## 2. Programme identity

- Programme: `OVC-PD-JUNE-2026-OPERATOR-REVIEW-AND-MARKET-DESCRIPTION-ASSURANCE.v0.1`
- Packet: `PD-JUNE-RA1`
- Baseline: `61fdea3a1b05ec941d867b5c6d181f6a401c2fc6`
- Parent pilot v1: `PD.PILOT.RUN.0cc5a59ca751583f3e50091c`
- Corrective pilot v2: `PD.PILOT.RUN.96c16f11717e787f971851ee`
- Source slice: `RPS.DUKASCOPY.GBPUSD.20260622_20260625.v1`
- Research role: `PILOT_DISCOVERY`
- Operation mode: `TIME_GATED_REPLAY`

## 3. Authority boundary

This plan authorises only deterministic, read-only synthesis of existing repository and preserved signed pilot evidence; contracts, schemas, fixtures, tests, QA and review packets; and a fail-closed reliability-assessment design.

This plan does **not** authorise:

- canonical 2021–2023 Discovery processing or append;
- another June machine replay or provider intake;
- pilot identity reuse or LIVE_PROSPECTIVE relabelling;
- trigger, formula, distance, cluster, threshold or model changes;
- semantic, family, candidate, novelty or theory promotion;
- selector or release mutation;
- R2 publication or Validation consumption;
- probability, risk, exposure, trading, execution or agent-write authority.

## 4. Questions to answer

1. What were the original and corrective operator dispositions for the six June queue-promoted objects?
2. Which findings were workflow defects, interface defects, missing evidence context, chronology contradictions or valid negative controls?
3. Which problems were corrected without changing market logic?
4. What can be concluded about deterministic computation, evidence lineage and review-workflow reliability?
5. Does the available evidence establish that the system consistently and reliably describes the market?
6. What exact evidence and tests are still required before that claim can lawfully be made?

## 5. Reliability dimensions

The assessment must keep these dimensions separate:

- **Computational reproducibility:** same governed input produces byte-identical derived output.
- **Lineage and evidence integrity:** source, release, selector, hashes and signatures are exact and verifiable.
- **Review-workflow reliability:** the operator can understand, reproduce and classify the candidate using the panel.
- **Internal structural consistency:** trigger chronology, candidate identity, fingerprint, medoid assignment, distance decomposition and outlier state agree with frozen rules.
- **External market-description validity:** each factual description agrees with the exact market path and does not omit material contradictory structure.
- **Population consistency:** reliability persists across a representative sample, including suppressed and negative-control objects.

A PASS in the first four dimensions must never be represented as proof of the final two.

## 6. Evidence basis

The packet may use the repository-retained gate packets, review receipts, correction ledgers, signed evidence indexes and exact hashes for the v1 and v2 June pilots. The large operator-local `review/console-bundle.json`, exact candidate price windows and raw derived JSONL remain external unless separately bound and returned.

## 7. Required packet outputs

- operator-review synthesis;
- market-description reliability assessment;
- claim-level reliability review contract;
- machine-readable programme state;
- QA and delegated decision records;
- focused tests and repository-wide verification.

## 8. Decision rule

The programme may conclude `PASS`, `CONDITIONAL_PASS`, `NOT_ESTABLISHED`, `BLOCKED` or `QUARANTINED` for each reliability dimension. It must fail closed when exact claim-to-market evidence is unavailable.

## 9. Current boundary

`PD-JUNE-RA1` ends after the evidence-based assessment and improvement specification. No canonical Discovery continuation follows automatically. A later packet may bind the operator-local June console bundle and exact market windows for claim-level validation, but only under a separate bounded continuation from the then-current lawful `main`.
