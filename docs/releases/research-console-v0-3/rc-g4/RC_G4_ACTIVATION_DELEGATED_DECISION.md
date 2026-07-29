# RC-G4 Activation — Delegated PASS Decision

- **Packet:** `RC-G4-ACTIVATION`
- **Decision:** `PASS`
- **Decision authority:** `DELEGATED_AUTO_RATIFICATION_WITHIN_OPERATOR_APPROVED_DELTA`
- **Operator gate:** `RC-G4 PASS`
- **Operator decision merge:** `19066a5201e33a51b0e785dbdc932999f39fd9da`
- **Baseline:** `19066a5201e33a51b0e785dbdc932999f39fd9da`
- **Tested candidate:** `0fd59862770b50f9bc678de44c2ca99aa5a04953`
- **Branch:** `activate/research-console-v0-3-rc-g4-c1`
- **Pull request:** `#152`
- **Authority delta:** `LOCAL_READ_ONLY_C1_PRESENTATION`

## Decision

PASS is recorded under the authority delegated by the operator's RC-G4 approval. The implementation activates only a local, read-only Research Console route for accepted RO3-G4 C1 projection objects. It does not grant any new authority beyond the exact operator-approved delta.

The route is `RESEARCH.C1_FACT_ASSURANCE / ENABLED_LOCAL_READ_ONLY`. Discovery and Development projections are accepted only under exact release, manifest, clock, side, schema-ID, Git-blob and lineage bindings. Validation remains `LOCKED_UNCONSUMED` and is denied before panel or record resolution.

## Evidence

- 12 focused RC-G4 activation tests: PASS.
- 12 accepted RO3-G4 adapter regression tests: PASS.
- 6 RC-G4 operator-gate regression tests: PASS.
- Dedicated complete repository suite, 70 tests: PASS.
- Independent generic complete repository suite, 70 tests: PASS.
- Exact authority-delta assertions: PASS.
- Dedicated workflow: run `30425811445`, job `90491943746`.
- Generic workflow: run `30425811401`, job `90491943701`.
- QA packet: `docs/releases/research-console-v0-3/rc-g4/RC_G4_ACTIVATION_QA_PACKET.json`.

## Retained boundaries

C1 formulas, releases and selectors remain immutable. C2 and Pattern Discovery authority remain unchanged. Downstream references are identity-only and structurally separated under the permanent authority banner. Research writes, Validation consumption, R2 publication, semantic or threshold changes, model/family/candidate/theory promotion, probability, risk, exposure, trading, execution, agent-write and remote-deployment authority remain denied.

## Rollback

Revert the bounded activation package through a new non-destructive commit and return the Console to the accepted RO2/RC-G3 local read-only presentation. Preserve the RC-G4 operator decision, RO3 evidence, all C1/C2/Pattern Discovery authority and selectors, and R2 objects.

## Merge eligibility

PR `#152` is eligible for squash merge after final-head checks pass and no unresolved review or base-change issue remains. After merge, record the exact main merge SHA and mark the programme completed.
