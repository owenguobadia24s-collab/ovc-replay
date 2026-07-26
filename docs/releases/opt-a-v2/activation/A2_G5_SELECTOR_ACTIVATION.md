# A2-G5 — OPT-A v2 selector-set activation

## Decision

**PASS — ACTIVATE.** The exact three A2-G4 remotely verified OPT-A v2 role releases are activated as one atomic selector set.

This decision activates sealed observation inputs only. It does not consume Validation, activate OPT-B/C/D, create probability or exposure authority, or authorise trading or execution.

## Activated selector set

Selector set: `SELECTOR.OPT-A.GBPUSD.ROLESET.v1`

| Role | Release | Manifest | Authority |
|---|---|---|---|
| Discovery | `OPT-A.GBPUSD.DISCOVERY.2021_2023.v2` | `MANIFEST.OPT-A.GBPUSD.DISCOVERY.2021_2023.v2.r2` | `ACTIVE_DISCOVERY` |
| Development | `OPT-A.GBPUSD.DEVELOPMENT.2024.v2` | `MANIFEST.OPT-A.GBPUSD.DEVELOPMENT.2024.v2.r2` | `ACTIVE_DEVELOPMENT` |
| Validation | `OPT-A.GBPUSD.VALIDATION.2025.v2` | `MANIFEST.OPT-A.GBPUSD.VALIDATION.2025.v2.r2` | `ACTIVE_VALIDATION / LOCKED_UNCONSUMED` |

Manifest SHA-256 identities:

- Discovery: `0cbcafa9421449574b61bfeec24f634de99cbbbc6e7a53d09ace8f702182ab8c`
- Development: `25e1be8a7edb0e96017c45bf35f4e788345f94b22a8ed9bb0874c86338ba64cc`
- Validation: `9d855d4c7dda01182a574cba96761c2f545266580307b2e2bc764af6d933b877`

## Preconditions reviewed

- A2-G4 remote-publication review: `PASS`
- all three release manifests remotely verified: `PASS`
- exact manifest binding: `PASS`
- one atomic selector-set update: `PASS`
- Validation lock preserved: `PASS`
- historical v1 reactivation prohibited: `PASS`
- rollback target to all selectors `NONE`: `PASS`

## Authority delta

After activation:

- OPT-A selector set: `ACTIVE`
- Discovery authority: `ACTIVE_DISCOVERY`
- Development authority: `ACTIVE_DEVELOPMENT`
- Validation identity selector: `ACTIVE_VALIDATION`
- Validation consumption: `LOCKED_UNCONSUMED`
- OPT-A-to-OPT-B active handoff: `NONE`
- OPT-B.C1 selector: `NONE`
- OPT-B.C2 selector: `NONE`
- OPT-C and OPT-D selectors: `NONE`
- probability, exposure, trading and execution: `DENIED`

Activation does not imply that any downstream layer may consume the selected releases without its own contract, work packet, QA and operator gate.

## Rollback

Rollback is an atomic selector-set transition from all three active role selectors to `NONE`. It does not delete, overwrite or alter any release or manifest. Historical `OPT-A.GBPUSD.2026H1.v1` remains prohibited as a rollback target.

## Next boundary

OPT-A v2 is complete as the active sealed observation foundation. The next bounded programme may begin with OPT-B.C1 v2 under its own implementation gates and exact active OPT-A parent binding.
