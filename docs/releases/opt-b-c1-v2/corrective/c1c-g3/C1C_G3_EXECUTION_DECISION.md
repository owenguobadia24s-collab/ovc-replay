# C1C-G3 — execution decision

**Decision:** `PASS`

The operator-approved C1 v2 publication gate completed under `OVC-C1-WICK-BALANCE-CORRECTIVE-PROGRAMME-0.1`.

## Exact execution

- Workflow run: `30384400312`
- Workflow commit: `1e2a1960ff0eb6747998453e5693cc82856524ba`
- Source candidate run: `30370847916`
- Publication order: payload first, manifest completion marker last
- Remote objects verified: `194`
- Remote bytes verified including manifests: `36,206,001`
- Receipt: `C1C_G3_REMOTE_VERIFICATION_RECEIPT.json`

## Published immutable releases

- `OPT-B.C1.GBPUSD.DISCOVERY.2021_2023.v2`
  - Manifest: `MANIFEST.C1.OPT-B.C1.GBPUSD.DISCOVERY.2021_2023.v2.r1`
  - Logical manifest SHA-256: `c9b2eaa826419a510504c016d99072c6015c337a5c2ef435252d5f6ff1db93bf`
  - Manifest file SHA-256: `708025a0f96db4649996bc1201da258f76c048723cf29b0c82725a19ba6418a9`
- `OPT-B.C1.GBPUSD.DEVELOPMENT.2024.v2`
  - Manifest: `MANIFEST.C1.OPT-B.C1.GBPUSD.DEVELOPMENT.2024.v2.r1`
  - Logical manifest SHA-256: `e4f1a2d0af7064837003f1c7b56156966aba3b035cc9a7b8ebbdc8b6b181d73f`
  - Manifest file SHA-256: `56c42c1d34d77670ffec25dcf86da6bd7726017c133f1bd9e4f4be2aba23633e`

## Authority

C1C-G3 changes publication availability only. The v2 releases remain inactive. C1 v1 and C2 v1 selectors remain unchanged pending the already-approved coordinated C1C-G4/G5 transaction. Validation remains `LOCKED_UNCONSUMED`. No semantic, threshold, family, novelty, probability, risk, exposure, trading, execution or agent-write authority is granted.

## Rollback

Preserve the published v2 bytes immutable and inactive and retain the exact v1 selectors.

## Next

Execute C1C-G5 deterministic C2 v2 identity replay and publication, then complete the coordinated C1C-G4/G5 selector replacement and noncanonical Pilot Discovery supersession/rerun.
