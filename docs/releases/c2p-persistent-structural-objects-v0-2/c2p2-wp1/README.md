# C2P2-WP1 — core contract and synthetic-pack constitution

Programme: `OVC-C2P-PERSISTENT-STRUCTURAL-OBJECTS-CONFORMANCE-v0.2`  
Packet: `C2P2-WP1` / Gate: `C2P2-G1`  
Current lawful baseline: `22c5ede9c6e7ccdeba26ea53e7a83890170b10dd`  
Initial WP1 implementation baseline: `fdf64e0df76c5f75b21de357bac05ec965b9f0f7`  
Branch: `build/c2p2-wp1-contracts-v3`  
Authority: AUTO-EXECUTABLE mechanical conformance only.

WP1 materialises the exact ratified core contract/schema/registry catalogue, canonical serialization profile, activation-ineligible synthetic ObjectPacks A/B, the core fixture/QA registries, and the reference canonicalizer needed by later synthetic packets. No C2P runtime is activated and no empirical ObjectPack is selected.

Prior WP1 PRs were superseded without force-push after the stable-main readiness lane detected lawful CI/main-head churn. The third packet is rebuilt from main `22c5ede...`, whose delta is CI workflow-inventory governance only and carries no C2P semantic or authority change.

## Acceptance surface

- 15 core contracts, 13 strict top-level schemas and 12 active core registries are present.
- `C2P_CANONICAL_SERIALIZATION_PROFILE_v0_2` freezes sorted keys, explicit nulls, canonical decimals, UTC `Z`, pre-normalized Unicode NFC and SHA-256; host floats/NaN/Infinity/negative zero and non-NFC identity strings fail closed.
- Synthetic packs `C2P.SYNTH.OBJECTPACK.MINIMAL.A.v1` and `.B.v1` are nonempirical, activation-ineligible and real-source-forbidden; exact pack hashes are pinned.
- Candidate, Tracklet, ObjectAssertion, event/projection/checkpoint field families conform to the revised design; Tracklet uses `CONFIRMED`, not a `PROMOTED` lifecycle state.
- Geometry and structural role remain separate registries. Lifecycle, observability and evaluation remain orthogonal.
- StructuralReferent/ReconciliationPack runtime remains namespace-reserved and deferred.
- Core QA catalogue = 37 assertions; core fixture catalogue = 39 fixtures; IDs are programme-namespaced. Deferred reconciliation/science items remain outside the core.

## Tests

`python -m unittest tests.opt_b.c2p.v0_2.test_c2p2_wp1_contracts`

Repository-wide CI and tiered final-head assurance are required on this exact PR head before G1 integration.

## Rollback

Before merge, close the bounded PR. After merge, forward-supersede contracts/registries; never silently mutate frozen identity semantics or activate a pack.
