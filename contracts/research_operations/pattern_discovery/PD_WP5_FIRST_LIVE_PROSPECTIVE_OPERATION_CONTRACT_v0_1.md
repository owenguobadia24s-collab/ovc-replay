# PD-WP5 First LIVE_PROSPECTIVE Operation Contract v0.1

## Governing authority

This contract implements the first operation permitted by the operator-approved `RPS-G4` decision and the exact activation merge `aa29b23a7a83e33880ac2d80deb013f0c0390f30`.

The operation is limited to:

- research line `RESEARCH.OPT-B.C2.GBPUSD.DISCOVERY.v1`;
- model `OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v1`;
- source binding `RPS.BINDING.32fb3003efa072916c11e907`;
- signing binding `RPS.SIGNING.50092c28981fef08f53a6cb5`;
- operator `OVC.OPERATOR.PRIMARY.LOCAL.V1`;
- one first operator-supervised candidate operation;
- mandatory stop at `PD-G5`.

## Strict activation cutoff

The admissibility cutoff is not copied from chat or manually entered. The operator-local command resolves the Git committer timestamp of activation merge `aa29b23a7a83e33880ac2d80deb013f0c0390f30`.

For a candidate to be LIVE_PROSPECTIVE:

- `market_window_start_utc` must be strictly after the activation cutoff;
- `market_window_end_utc` must be strictly after the activation cutoff;
- `trigger_first_valid_at` must be strictly after the activation cutoff and inside the market window;
- immutable source-object IDs must resolve;
- the exact active release, manifest, source binding, signing binding and operator must match.

Replay, fixtures and pre-activation market windows cannot satisfy this contract.

## Current source-coverage blocker

The activated source binding declares `eligible_data_through_utc = 2026-06-25T00:00:00Z`. The activation merge occurred on 27 July 2026. Therefore the exact active binding has no market coverage capable of producing a candidate strictly after activation.

This is a source-authority blocker, not a trigger, fingerprint, queue or review defect. It cannot be resolved by:

- relabelling TIME_GATED_REPLAY as LIVE_PROSPECTIVE;
- using the June replay output;
- filling, extrapolating or synthesising bars;
- manually entering source IDs;
- changing the activation cutoff;
- weakening chronology or lineage checks.

## RPS-G4A amendment candidate

The smallest lawful resolution is one operator amendment for a post-activation source slice:

- gate: `RPS-G4A`;
- provider: Dukascopy;
- instrument: GBP/USD;
- slice: `RPS.DUKASCOPY.GBPUSD.20260728_20260801.v1`;
- interval: `[2026-07-28T00:00:00Z, 2026-08-01T00:00:00Z)`;
- streams: M1 BID, M1 ASK, native H1 BID, native H1 ASK;
- compressed limit: 25 MiB;
- expanded limit: 100 MiB;
- destination: external-artifact root only;
- no provider request before approval;
- no provider access in CI;
- no M1-derived substitution for native H1.

Execution must defer until Dukascopy makes the July 2026 native-H1 monthly BI5 objects available. Approval would permit only the exact bounded intake and subsequent deterministic source acceptance, compute, binding and one PD-WP5 operation.

## Preflight command

The operator-local command:

```text
python -m ovc.research_operations.pattern_discovery.first_live_operation preflight
```

must:

1. require clean local `main` containing the activation merge;
2. derive the activation cutoff from Git;
3. validate exact activation authority;
4. compare active-binding coverage with the cutoff;
5. reject replay and pre-activation candidate packages;
6. perform no provider request;
7. emit one compact blocker and amendment proposal.

The current expected result is:

`BLOCKED_POST_ACTIVATION_SOURCE_REQUIRED`

with exit code `3`, denoting an expected external/authority blocker rather than an implementation failure.

## Retained prohibitions

No provider request, canonical append, automatic evidence creation, autonomous processing, active novelty ranking, semantic promotion, C2E/C2.5/C3, selector/release/R2 mutation, Validation, probability, risk, exposure, trading, execution or agent write is authorised by this command-ready packet.

## Rollback

Revert the diagnostic command and blocker packet while preserving the RPS-G4 decision, activation, external key, source, compute, signed acceptance and quarantines. Do not deactivate RPS-G4 merely because no post-activation source exists; candidate append remains fail-closed.
