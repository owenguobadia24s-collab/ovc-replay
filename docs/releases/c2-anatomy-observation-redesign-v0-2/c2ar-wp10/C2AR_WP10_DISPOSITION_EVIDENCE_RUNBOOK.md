# C2AR-WP10 Disposition Evidence — Operator Runbook

Status: `IMPLEMENTED_PENDING_OPERATOR_LOCAL_COMPACT_ANALYSIS`  
Gate retained: `CEAR-G10`  
Authority: inactive, noncanonical, research evidence only.

## Purpose

The June vNext full replay has completed and passed two-clean-run, determinism, capacity and checkpoint/restart assurance. The replay deliberately emitted bulk population artifacts but did not create the compact operator-disposition surface required by Part 10.

This packet reads the existing completed replay without modifying it and emits one compact evidence record containing:

- exact replay, input-binding and manifest hashes;
- complete opportunity and evaluation reconciliation;
- functional-core and rule-candidate lineage;
- matched-control coverage and explicit counterexample counts;
- clock, side, sequence-length, week and month-half stability surfaces;
- pairwise match-population redundancy and co-occurrence;
- preregistered support, family-distance and component-frequency perturbations;
- legacy benchmark comparison when a lawful opportunity-ID manifest exists;
- explicit `DEFER` recommendation when legacy outputs cannot be lawfully mapped to vNext opportunity identities.

No bulk market, C1, opportunity, fingerprint, motif, family, evaluation or control payload enters Git.

## Clean worktree

Run from a clean checkout of `build/c2ar-wp10-disposition-evidence` at the exact assured packet head. Set the existing external evidence root:

```powershell
$env:OVC_EXTERNAL_ARTIFACT_ROOT = "C:\Users\Owner\OVIS\ovc-replay-external-artifacts"
git status --short
```

`git status --short` must produce no output.

## Build compact evidence

```powershell
.\scripts\c2ar\run_vnext_disposition_evidence.ps1
```

Default completed replay root:

```text
$env:OVC_EXTERNAL_ARTIFACT_ROOT\c2-anatomy-redesign-v0-2\wp10-rules\june-vnext-full-replay
```

Default output:

```text
<replay-root>\disposition-evidence\CEAR_G10_DISPOSITION_EVIDENCE.json
```

The source replay remains immutable. A failed receipt, manifest mismatch, incomplete evaluation, hidden control fallback, authority drift or missing lineage terminates the command without producing a valid record.

## Optional lawful legacy benchmark manifest

A legacy comparison may be supplied only when its entries use the exact vNext opportunity identities from this replay and are marked `benchmark_only: true`:

```powershell
.\scripts\c2ar\run_vnext_disposition_evidence.ps1 `
  -LegacyBenchmarkManifest "C:\path\to\legacy-benchmark-input.json"
```

Do not translate timestamps or legacy CandidateWindow IDs into vNext opportunity IDs by approximation. Without a lawful identity crosswalk, the compact record preserves two benchmark mapping slots and recommends `DEFER`; it does not assert `NOT_RECOVERED` or `CONTRADICTED`.

## Completion check

The output must report:

```text
status = GATE_READY_OPERATOR_DISPOSITIONS_REQUIRED
qa_recommendation = GATE_READY_OPERATOR_DECISION
active = false
canonical = false
```

All authority fields must remain `DENIED`, and every method/candidate/mapping decision field must remain null pending the operator.

After the compact record is created, return with:

```text
OVC CONTINUE
```

## Stop boundary

Do not merge PR #319 to main and do not begin WP11. CEAR-G10 remains operator-required. This analysis grants no method admission, functional/rule-candidate PASS, research-consumer permission, selector, event, episode, semantic, outcome, publication, Validation, probability, risk, exposure, trading, execution or agent-write authority.
