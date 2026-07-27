# RPS-G1B — Explicit Gapped-Source Acceptance Amendment

## Gate identity

- Gate: `RPS-G1B`
- Title: Explicit GAPPED acceptance for the checksum-pinned June quarantine
- Plan: `OVC-C2-REAL-PROSPECTIVE-SOURCE-PD-WP5-ENABLEMENT-PLAN-0.1`
- Plan version: `0.1`
- Packet: `RPS-WP2`
- Baseline main: `6aaa898727be83ebf3e5c32ebca129d38e629adb`
- Candidate implementation commit: `4e4c58799258f4bc87bac299affcec1c6ea57f7e`
- Tested PR merge ref: `3de50d7e1ae24fbc7f47382dba2577e740283ee0`
- Candidate branch: `build/rps-g1b-gapped-source-amendment`
- Pull request: `#103`
- Gate status: `GATE_READY`
- Authority: `OPERATOR_REQUIRED`

## Completed work

1. Recorded the RPS-G1A June source-QA incident without raw bytes, machine paths or mutable external evidence in Git.
2. Frozen an exact GAPPED acceptance contract for the June slice and exact June quarantine identity.
3. Added a no-network checksum inventory and copy-on-verify recovery command.
4. Added immutable enumeration of every absent M1 timestamp and gap run.
5. Added fail-closed BID/ASK, native-H1 and exact complete-hour reconciliation checks.
6. Added 15M, M1-derived H1 and 2H coverage propagation with incomplete-parent rejection and no synthesis.
7. Added QA-receipt materialisation before recovery pass/fail quarantine.
8. Added schemas, Windows operator guidance, tests, CI denial and machine-readable programme state.

## Current authority

RPS-G1A authorised one exact local Dukascopy request for `RPS.DUKASCOPY.GBPUSD.20260622_20260625.v1`. That request completed transport intake but did not create an accepted source slice because the M1 stream contained provider-absent minutes under a COMPLETE-only policy.

The source remains quarantined. Current authority does not permit reclassifying it as `GAPPED`, freezing it under the approved slice identity, or consuming it downstream.

## Operator evidence baseline

| Evidence | Observed result |
|---|---|
| M1 BID | 4,285 rows; 35 absent minutes; 24 gap runs |
| M1 ASK | 4,285 rows; identical timestamp set and absences |
| M1 boundaries/order | Complete boundaries; no duplicate or non-monotonic rows |
| BID/ASK | Exact pairing; no inverted rows |
| Native H1 | 72 rows per side; complete and paired |
| Reconciliation | 64 complete M1-derived H1 bars per side; zero OHLC mismatches |
| Accepted source slice | None |
| Source quarantine | Preserved operator-local |

GitHub has not received the raw bytes and cannot independently calculate their SHA-256 values at this gate.

## Proposed authority delta

Approve one checksum-pinned, no-network re-evaluation of only:

- slice `RPS.DUKASCOPY.GBPUSD.20260622_20260625.v1`;
- quarantine `RPS.DUKASCOPY.GBPUSD.20260622_20260625.v1.20260727T160337Z.38a69acd`;
- interval `[2026-06-22T00:00:00Z, 2026-06-25T00:00:00Z)`;
- M1 BID/ASK and native H1 BID/ASK;
- maximum 25 MiB compressed and 100 MiB expanded;
- result `coverage_state: GAPPED` only when all frozen acceptance conditions pass.

The command may calculate and freeze the local quarantine checksum inventory, copy verified transport bytes into a new staging workspace, materialise QA evidence and freeze one local immutable GAPPED source slice. It may not contact Dukascopy or any other provider.

## Acceptance conditions

1. The exact source quarantine contains only the original incident and eight expected BI5 files.
2. Observed transport byte sizes match the operator diagnostic.
3. A local checksum inventory records every path, byte size and SHA-256 and receives a canonical SHA-256.
4. The inventory is revalidated immediately before copy and every copied file is re-hashed.
5. The original quarantine is unchanged before and after the copy.
6. M1 BID and ASK each have exactly 4,285 rows, 35 missing timestamps and 24 gap runs.
7. The two M1 timestamp sets are identical; boundaries are complete; duplicates and non-monotonic rows are zero.
8. Native H1 BID and ASK each have 72 complete, paired rows.
9. Exactly 64 complete M1-derived H1 bars per side reconcile to native H1 with no missing native timestamp or OHLC mismatch.
10. Every absent timestamp and gap run is recorded.
11. Incomplete 15M, M1-derived H1 and 2H parents are marked unavailable and rejected; none is synthesized.
12. QA receipts are written before a failed recovery staging quarantine.
13. The frozen result is `GAPPED`, `NOT_A_RELEASE`, selector-ineligible, R2-denied, Validation-denied and LIVE_PROSPECTIVE-denied.
14. Provider network access is denied in CI and by the recovery command.

## Tests and QA

### Implemented checks

- exact 4,285-row/35-minute/24-run GAPPED fixture acceptance;
- exact M1 timestamp-set equality;
- complete 72-row native-H1 and 64-hour reconciliation;
- immutable missing-timestamp and gap-run receipts;
- downstream 15M/H1/2H unavailable-parent propagation;
- executable incomplete-parent rejection;
- checksum inventory creation and canonical hash verification;
- copy-on-verify and source-quarantine non-mutation;
- checksum-tamper rejection;
- mismatched BID/ASK gap rejection with QA receipts preserved before quarantine;
- exact gate binding and CI execution denial;
- canonical repository test discovery.

### Executed CI evidence

- Canonical workflow: `30286571687`
- Canonical unit-test job: `90045733438`
- Checked-out PR merge ref: `3de50d7e1ae24fbc7f47382dba2577e740283ee0`
- Command: `PYTHONPATH=src python3 -m unittest discover -s tests -v`
- Result: `PASS`
- Provider request performed: `false`
- External quarantine accessed: `false`

The canonical discovered suite included the new RPS-G1B generated-BI5 tests and existing RPS-G1A/base intake regression tests. The dedicated amendment workflow definition additionally specifies JSON parsing, focused suites and explicit CI freeze denial for future execution once present on `main`.

### QA recommendation

`PASS`. The candidate is deterministic, bounded, fail-closed and non-activating. No blocking implementation defect, review warning or inconsistent authority record remains in the packet. The proposed source-integrity delta remains operator-reserved despite passing QA.

## Warnings and unresolved issues

- GitHub cannot access the operator's local quarantine or calculate its actual hashes.
- The local inventory hash is not known until the operator runs `inventory` after approval.
- The source remains incomplete at M1. GAPPED acceptance does not make missing rows present.
- Later processing must consume the downstream coverage receipt and exclude incomplete parents.
- Any divergence from the frozen counts, timestamp-set equality, boundaries, H1 inventory or reconciliation blocks the freeze.

## Changed files

- `contracts/research_operations/prospective_source/RPS_GAPPED_SOURCE_ACCEPTANCE_CONTRACT_v0_1.md`
- `schemas/research_operations/prospective_source/quarantine_checksum_inventory_v0_1.schema.json`
- `schemas/research_operations/prospective_source/gapped_source_qa_v0_1.schema.json`
- `src/ovc/research_operations/prospective_source/gapped_source_contract.py`
- `src/ovc/research_operations/prospective_source/gapped_source_qa.py`
- `src/ovc/research_operations/prospective_source/dukascopy_gapped_recovery.py`
- `tests/research_operations/prospective_source/test_dukascopy_gapped_recovery.py`
- `scripts/run_rps_wp2_intake.ps1`
- `.github/workflows/rps-g1b-gapped-source-amendment.yml`
- `docs/releases/prospective-source-v0-1/rps-g1b/RPS_G1A_JUNE_SOURCE_QA_INCIDENT.md`
- `docs/releases/prospective-source-v0-1/rps-g1b/RPS_G1B_WINDOWS_OPERATOR_GUIDE.md`
- `docs/releases/prospective-source-v0-1/rps-g1b/RPS_G1B_QA_PACKET.md`
- this gate packet
- `registries/research_operations/prospective_source/REAL_PROSPECTIVE_SOURCE_IMPLEMENTATION_REGISTRY_v0_1.yaml`

## External artifact hashes

None are admitted at this gate. Exact hashes remain operator-local and must be produced by the approved inventory command after PASS.

## Authority retained as denied

Another provider request, another quarantine, gap repair, interpolation, forward fill, synthetic candles, incomplete-parent consumption, ACTIVE_RESEARCH_TRIAGE, LIVE_PROSPECTIVE append, live Pattern Discovery processing, active novelty ranking, selector/release/R2 mutation, Validation consumption, semantic or theory promotion, C2E/C2.5/C3, OPT-C/OPT-D, probability, risk, exposure, trading, execution and agent write remain denied.

## Rollback

Close PR #103 without merge and retain `main` at `6aaa898727be83ebf3e5c32ebca129d38e629adb`. Preserve the July and June source quarantines. No provider source, accepted slice, selector, release, R2 key, evidence row or active authority is changed by rollback.

## Recommended decision

**PASS** — approve exact checksum-pinned GAPPED re-evaluation and local freeze for the named June quarantine only.

Allowed decisions: `PASS`, `DEFER`, `BLOCK`, `QUARANTINE`, `SUPERSEDE`.

## Exact work after approval

1. Record the RPS-G1B operator decision.
2. Pin the final PR head and confirm required checks remain PASS.
3. Squash-merge the bounded amendment PR into `main`.
4. Pull `main` locally.
5. Run `preflight`, `inventory`, then `freeze` from the Windows operator guide.
6. Supply the compact manifest and eight compact receipt files.
7. Resume RPS-WP2 and evaluate RPS-G2.

## Approval command

```text
OVC APPROVE RPS-G1B
```
