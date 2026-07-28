# C1C-G3 / C1C-G4 / C1C-G5 — Operator Decision

**Decision:** `PASS`

**Authority:** Operator-reserved approval supplied by command:

```text
OVC APPROVE C1C-G3 C1C-G4 C1C-G5
```

**Decision date:** `2026-07-28`

**Programme:** `OVC-C1-WICK-BALANCE-CORRECTIVE-PROGRAMME-0.1`

**Gate packet:** `docs/releases/opt-b-c1-v2/corrective/C1C_G3_G4_G5_CONSOLIDATED_OPERATOR_GATE_PACKET.json`

## Approved authority deltas

### C1C-G3 — C1 v2 R2 publication

Authorise collision-preflight, immutable publication and full remote byte verification of only these exact local candidates:

- `OPT-B.C1.GBPUSD.DISCOVERY.2021_2023.v2`
  - manifest: `MANIFEST.C1.OPT-B.C1.GBPUSD.DISCOVERY.2021_2023.v2.r1`
  - manifest SHA-256: `c9b2eaa826419a510504c016d99072c6015c337a5c2ef435252d5f6ff1db93bf`
  - artifact: `8692836156`
  - artifact digest: `sha256:9cec2ff4391576334149cb4a3542131b2692530829d9794c4038354a4a299bf7`
- `OPT-B.C1.GBPUSD.DEVELOPMENT.2024.v2`
  - manifest: `MANIFEST.C1.OPT-B.C1.GBPUSD.DEVELOPMENT.2024.v2.r1`
  - manifest SHA-256: `e4f1a2d0af7064837003f1c7b56156966aba3b035cc9a7b8ebbdc8b6b181d73f`
  - artifact: `8692837001`
  - artifact digest: `sha256:fa5e02c23a834b0d6c1c9496635b6a5fcda8fbf3b9354fe3cc8ab363ea6937d1`

Publication must remain payload-first, manifest-last, immutable and fully read-back verified. Existing v1 selectors remain active until C1C-G4 execution passes.

### C1C-G4 — C1 selector replacement

After both exact C1 v2 releases are remotely verified, authorise one atomic replacement of the Discovery and Development C1 selectors from v1 to their exact v2 release and manifest identities.

Rollback must atomically restore the exact v1 selector release and manifest hashes. Validation remains `LOCKED_UNCONSUMED`.

### C1C-G5 — downstream identity remediation

After exact C1 v2 remote verification, authorise deterministic C2 Discovery and Development identity replay against the exact C1 v2 parents, publication and full remote verification under new immutable C2 v2 identities, followed by coordinated C1/C2 selector replacement.

Any C2 state or transition value drift is blocking. Canonical Pattern Discovery append remains prohibited. The noncanonical June 2026 Pilot Discovery namespace must be superseded append-only and rerun under its existing `PILOT_ONLY`, `TIME_GATED_REPLAY`, `NON_PROMOTABLE` constraints.

## Retained prohibitions

This decision grants no Validation consumption, semantic or family promotion, novelty promotion, threshold change, canonical Pattern Discovery append, probability, risk, exposure, trading, execution or agent-write authority.

## Rollback

- C1C-G3: keep v2 immutable and inactive; retain v1 selectors.
- C1C-G4: restore exact C1 v1 selectors atomically.
- C1C-G5: restore exact C1/C2 v1 selectors atomically, keep v2 releases inactive and immutable, preserve pilot supersession, and never reactivate legacy B-state.

## Continuation

Execute C1C-G3, then C1C-G5 identity replay/publication, then the coordinated C1C-G4/C1C-G5 selector transaction. On PASS, rerun `RO3-WP3_RETEST_AFTER_C1_CORRECTIVE_PROGRAMME` and continue the ratified RO3 plan.