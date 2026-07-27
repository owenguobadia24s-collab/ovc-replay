# RPS-G3 — Derived Compute Evidence QA Packet

- Plan: `OVC-C2-REAL-PROSPECTIVE-SOURCE-PD-WP5-ENABLEMENT-PLAN-0.1` v0.1
- Packet: `RPS-WP3`
- Gate: `RPS-G3`
- Baseline main: `2fbcc114d55858c95fbfefe743fb98ba5800560b`
- Source slice: `RPS.DUKASCOPY.GBPUSD.20260622_20260625.v1`
- Compute run: `RPS.RUN.7aeb551335d766ee3bf503e6`
- Binding candidate: `RPS.BINDING.32fb3003efa072916c11e907`
- QA recommendation: `PASS`

## Compact evidence verification

The five operator-supplied compact files were read as UTF-8 JSON and byte-hashed. Their sizes and SHA-256 values are pinned in `RPS_WP3_COMPACT_COMPUTE_EVIDENCE_INDEX.json`.

The following invariants were reproduced:

1. output-manifest logical SHA-256 `3c6295badd04896a9e94b4b5a3ccb354bb51de52d5927839a86f61a40ed679ff`;
2. output-manifest file SHA-256 `af0410d58f8b6522129a0162f9741c6b7bc5485526848d64199cdbc60256f7be`;
3. compute-run file SHA-256 `c25632febb84a8d3604390988a042fa8b30e1484381a17d4201ab58388e78e41`;
4. binding file SHA-256 `d4cf2c272b4b7125a89cbf95b3b8943a2e68e8b2027608eafda058d6159ac576`;
5. deterministic run ID recomputation to `RPS.RUN.7aeb551335d766ee3bf503e6`;
6. deterministic binding ID recomputation to `RPS.BINDING.32fb3003efa072916c11e907`;
7. exact source manifest and slice identity across all compact files;
8. exact code commit `2fbcc114d55858c95fbfefe743fb98ba5800560b`;
9. exact admissible cutoff `2026-06-25T00:00:00Z`;
10. exact `TIME_GATED_REPLAY` operation mode.

## Coverage closure

Per side, the run records:

| Clock | Total | Complete | Unavailable | Policy |
|---|---:|---:|---:|---|
| 15M | 288 | 271 | 17 | `EXCLUDE_NO_SYNTHESIS` |
| 2H_A_L | 36 | 30 | 6 | `EXCLUDE_NO_SYNTHESIS` |

The totals close to:

- 602 C1 records;
- 1,144 C2 state records;
- 954 C2 transition records;
- 21 payload files;
- 5,557,327 declared payload bytes.

The uploaded `coverage.json` byte hash matches the coverage object declared by the output manifest.

## Gap and lineage controls

- coverage state: `GAPPED`;
- QA state: `PASS_GAPPED_EXCLUSION`;
- deterministic replay: true;
- lineage complete: true;
- repair performed: false;
- forward fill performed: false;
- interpolation performed: false;
- synthesis performed: false;
- incomplete-parent consumption: `DENIED`.

## Authority assessment

The compute run and binding remain local derived candidates only:

- release status `NOT_A_RELEASE`;
- selector eligibility `NONE`;
- R2 publication `DENIED`;
- Validation consumption `DENIED`;
- LIVE_PROSPECTIVE append `DENIED`;
- ACTIVE_RESEARCH_TRIAGE false;
- write authority false;
- provider network access false;
- exposure authority `NONE`.

Accepting these compact identities introduces no operator-reserved activation or publication authority. RPS-G3 is therefore eligible for delegated auto-ratification inside the ratified plan's derived-local-compute envelope.

## Warnings

The repository does not contain the 21 derived payload files and did not independently re-read those payload bytes. It accepts their exact manifest identities only through the deterministic local command, the compact receipt chain and the pinned coverage byte. No raw or derived market payload is committed.

## Rollback

Revert the RPS-G3 acceptance records and return RPS-WP3 to `RUNNING_AWAITING_OPERATOR_LOCAL_COMPUTE_EVIDENCE`. Preserve the accepted source slice, compute run directory and all quarantines. Do not delete, mutate, relabel or republish any external artifact.
