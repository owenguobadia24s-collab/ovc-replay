# PD-WP5 Pilot Discovery Implementation Packet

## Packet identity

- Packet: `PD-WP5-PILOT`
- Parent packet: `PD-WP5`
- Amendment gate: `PD-G4B`
- Acceptance gate: `PD-G5P`
- Research role: `PILOT_DISCOVERY`
- Operation mode: `TIME_GATED_REPLAY`
- Status: `PLANNED_PENDING_OPERATOR_APPROVAL`

## Exact inputs

| Input | Exact identity |
|---|---|
| Source slice | `RPS.DUKASCOPY.GBPUSD.20260622_20260625.v1` |
| Coverage | `GAPPED` |
| Compute run | `RPS.RUN.7aeb551335d766ee3bf503e6` |
| Output manifest | `3c6295badd04896a9e94b4b5a3ccb354bb51de52d5927839a86f61a40ed679ff` |
| Source binding | `RPS.BINDING.32fb3003efa072916c11e907` |
| Signed replay acceptance | `RPS.REPLAY-ACCEPT.0844eddf74e144ced487cc48` |
| Signing binding | `RPS.SIGNING.50092c28981fef08f53a6cb5` |
| Operator | `OVC.OPERATOR.PRIMARY.LOCAL.V1` |
| Active C2 model | `OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v1` |

## Work after PD-G4B PASS

1. Create an isolated `PD-WP5-PILOT` implementation branch from the approved merge on `main`.
2. Add a pilot-only runner that reads the exact accepted external compute payloads and performs no provider request.
3. Execute trigger evaluation under the admissible cutoff and first-valid chronology rules.
4. Construct bounded candidate windows and record all exclusions.
5. Apply queue caps, suppression, merge, batching and backpressure with explicit receipts.
6. Build deterministic fingerprints and run provisional clustering.
7. Generate pilot candidate, cluster, medoid and assignment identities only in `PD.PILOT.GBPUSD.20260622_20260625.v1`.
8. Project the pilot through the Research Console with permanent pilot banners and no canonical population mixing.
9. Capture operator review and signed pilot evidence in an append-only pilot namespace.
10. Rerun the complete pilot from the same source and compare every identity, byte hash, count and ordering result.
11. Produce the defect/correction ledger, performance evidence and final versioned contract candidate.
12. Stop at `PD-G5P`.

## Required implementation artifacts

- pilot operation contract and machine-readable profile;
- candidate, queue, fingerprint, cluster, review and pilot-evidence schemas or explicit profile extensions;
- operator-local command and Windows guide;
- deterministic input/output manifest and receipts;
- queue-cap and batching receipt;
- coverage and missingness propagation receipt;
- deterministic rerun comparison;
- clustering runtime and memory report;
- Console pilot projection and banner assertions;
- signed pilot-evidence inventory;
- defect/correction ledger;
- final-contract candidate and identity-reset plan;
- focused tests, canonical tests and QA packet;
- consolidated `PD-G5P` operator packet.

## Fail-closed conditions

The pilot must stop and quarantine its candidate workspace if:

- any exact input identity or hash differs;
- any record reads information after its admissible cutoff;
- any incomplete parent is consumed or repaired;
- any pilot record lacks `PILOT_ONLY` and `NON_PROMOTABLE` markings;
- any pilot ID enters a canonical namespace;
- deterministic rerun identities or hashes differ without a named incident;
- the Console omits the pilot banner or mixes pilot and canonical counts;
- signed evidence cannot resolve the operator and signing binding;
- queue overflow is silently dropped;
- clustering becomes nondeterministic;
- any forbidden authority is requested.

## Pilot corrections

Correctable operational defects may be repaired on the bounded packet branch and rerun. Every correction must record:

- defect ID and symptom;
- affected component and output identities;
- root cause;
- changed files and versions;
- tests added or changed;
- before/after deterministic evidence;
- whether the final canonical contract changes;
- rollback.

No correction may be selected because it improves an observed market outcome.

## Exit

The packet cannot complete automatically. It ends at `PD-G5P — Pilot Discovery Operations Acceptance`, where the operator decides whether the operating workflow is sufficiently concrete and reproducible to freeze before the 2021–2023 canonical Discovery population.
