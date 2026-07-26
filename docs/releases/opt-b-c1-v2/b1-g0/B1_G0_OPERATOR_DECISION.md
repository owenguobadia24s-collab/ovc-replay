# OPT-B.C1 v2 B1-G0 Operator Decision

## Decision

`PASS — WP3 REFERENCE ENGINE APPROVED; BOUNDED WP4 REPLAY SCOPE AUTHORISED`

## Reviewed baseline

- Repository baseline: `8a4852358324a4e6dfc9f7c239be9e9eb8d69c23`
- WP3 implementation merge: `d5c0f1a9053f837ee85e2b478fba0662a133cc29`
- Formula registry: `C1.FORMULAS.v0.1`
- WP3 state: fixture-trust pass with deterministic Decimal computation, canonical serialization and no market authority

## Review conclusion

The WP3 reference engine is accepted as fit for a bounded market replay because its tests establish exact Decimal arithmetic, deterministic identity, strict contiguous-prior-close use, explicit null reasons, canonical-clock and price-side enforcement, Validation-lock enforcement and rejection of legacy or control-only inputs.

This decision does not promote synthetic outputs into market evidence. It authorises the same frozen engine to read only the exact active OPT-A v2 Discovery and Development release artifacts named in `C1_WP4_REPLAY_SCOPE.yaml`.

## Approved WP4 scope

- Instrument: `GBPUSD`
- Roles: Discovery 2021–2023 and Development 2024
- Clocks: `15M`, `2H_A_L`
- Sides: `BID`, `ASK`, separate
- Inputs: accepted observations from exact remotely verified OPT-A v2 manifests
- Outputs: external mutable replay workspace only
- Formula set: exactly `C1.FORMULAS.v0.1`

Validation 2025 remains identity-visible but `LOCKED_UNCONSUMED` and is excluded from WP4.

## Mandatory WP4 evidence

WP4 must produce deterministic replay outputs, an exact external inventory, counts by role/clock/side, null-reason counts, rejected-source counts, quarantine-exclusion proof, rerun identity checks and a compact QA packet. No missing observation may be filled or substituted.

## Authority retained

WP4 market replay is authorised only inside the exact scope. Local release freeze remains denied until the WP4 QA packet passes and receives a separate operator decision. R2 publication, C1 selector activation, C2 consumption, probability, exposure, trading and execution remain denied.

## Rollback

Rollback deletes any unfrozen WP4 workspace and returns C1 to the WP3 fixture-trust state. OPT-A selectors and all C1 selectors remain unchanged.

## Next work packet

`OPT-B.C1 v2 WP4 — Discovery and Development market replay, QA and local candidate release`
