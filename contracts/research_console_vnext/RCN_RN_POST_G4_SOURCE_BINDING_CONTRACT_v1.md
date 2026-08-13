# RCN-RN Post-G4 Owner Read Projection Binding Contract v1

## Authority
This contract implements only the operator-approved `RCN-RN-G4 PASS` delta. It grants no new authority. MARKET/OPT-A, C1, C2 and C2E may be presented through GET/read-model routes from already-materialised local owner projections. C2P, C2.5 and C3 remain excluded from real-source presentation.

## Binding model
Real mode is explicit through `OVC_RCN_INVESTIGATE_SOURCE_MODE=REAL`. Fixture mode remains explicit and is the default for the deterministic console fixture pack. **Real mode never falls back to fixture data.** Each real binding reads only a local owner-projection JSON object identified by the binding registry. The adapter performs no provider intake and no scientific, semantic, threshold, model, family, candidate, theory, event, transition or episode synthesis.

A present owner projection must carry exact source identity, first-valid chronology/cutoff, missingness numerator/denominator, QA/provenance and a fail-closed read-only authority envelope. A missing owner projection returns typed `NOT_MATERIALIZED`; an invalid or mismatched projection fails closed.

## Invariants
- source owner remains authoritative;
- Validation is rejected before protected source resolution/read;
- GET only; POST/PUT/PATCH/DELETE remain denied;
- no provider fetch or new instrument/market/clock/side/dependency;
- no fixture or lower-layer fallback in real mode;
- C2 is independently presentable when C2E is unavailable;
- C2E is never reconstructed from C2;
- transitions are never synthesized from C2 deltas;
- C2P/C2.5/C3 real routes remain denied;
- a Research Console response has authority effect `NONE`; it reports prior G4 presentation authority rather than granting authority.

## Rollback
Disable real mode/remove the four post-G4 bindings and return to explicit fixture-only presentation. Preserve source-owner data, G4 decision evidence and Git history.
