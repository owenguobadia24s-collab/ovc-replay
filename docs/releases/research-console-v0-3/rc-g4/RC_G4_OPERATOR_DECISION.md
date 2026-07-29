# RC-G4 Operator Decision

- **Gate:** `RC-G4`
- **Decision:** `PASS`
- **Decision authority:** `OPERATOR`
- **Operator instruction:** `@GitHub OVC APPROVE RC-G4 PASS`
- **Recorded date:** `2026-07-29`
- **Plan:** `OVC-RESEARCH-OPERATIONS-FOUNDATION-v0.3-C1-FACT-ASSURANCE-IMPLEMENTATION-PLAN-0.2` v0.2
- **Gate baseline:** `80adf5cfb111a8b07788276c9867ff4fee32fb09`
- **Gate branch:** `gate/rc-g4-c1-live-consumption`
- **Gate packet:** `docs/releases/research-console-v0-3/rc-g4/RC_G4_C1_CONSUMPTION_OPERATOR_GATE_PACKET.json`
- **RO3-G4 merge:** `80adf5cfb111a8b07788276c9867ff4fee32fb09`

## Approved authority delta

`LOCAL_READ_ONLY_C1_PRESENTATION`

Research Console v0.3 may consume exact accepted RO3-G4 projection objects locally and read-only. Discovery and Development C1 facts, computability, assurance and upstream lineage may be presented in distinct panels. Identity-only downstream C2 and Pattern Discovery references may appear only in a separate panel carrying the permanent authority banner:

> **DOWNSTREAM TRACE — READ ONLY. C2 AND PATTERN DISCOVERY AUTHORITY IS UNCHANGED.**

Validation remains metadata-only and `LOCKED_UNCONSUMED`.

## Retained prohibitions

This PASS grants no research-write expansion; formula, release, selector or threshold mutation; C1, C2 or Pattern Discovery recomputation, tuning, scoring or promotion; Validation consumption; R2 publication; semantic, model, family, candidate or theory promotion; probability, risk, exposure, trading, execution, agent-write or remote-deployment authority.

## Activation boundary

The gate decision does not itself activate the route. The route remains `DISABLED_PENDING_RC_G4_ACTIVATION` until a bounded activation implementation is built, tested, QA-approved and squash-merged. That implementation must accept only the four approved RO3-G4 schema identities, fail closed on stale or malformed projections, preserve panel separation and expose no write capability.

## Evidence accepted

- RO3-G4 adapter artifact `8712249496`, digest `sha256:44e4a533c153454c79009e2c8be196d6d9b543dcb869c5ac85cc5e8b63f86c05`.
- Full evidence payload SHA-256 `a08b8ec0d3cb848076d8fdad884ac9f763a1b34beae123272290c396ccfb5c84`.
- RO3-WP4: 12 focused tests PASS and 70 repository tests PASS.
- RC-G4 gate validation run `30422562947`, job `90482181971`: PASS.
- RC-G4 complete repository run `30422562930`, job `90482181958`: PASS.
- No-write, Validation denial, stale projection, missing trace, mixed-panel, downstream-scoring and pre-gate activation rejection evidence: PASS.

## Rollback

Disable the C1 route and return Research Console v0.3 to the accepted RO2/RC-G3 local read-only state. Preserve RO3 projection objects, evidence and decisions, all C1/C2/Pattern Discovery authority and selectors, and R2 objects. Do not rewrite history or delete court-record evidence.

## Continuation

After this decision record is merged, create a fresh bounded activation branch from lawful `main`, implement and test local read-only consumption, materialise the RC-G4 acceptance registry and activation receipt, then squash-merge if the final delta remains wholly inside this approval.
