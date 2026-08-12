# OVC EI-WP1 Contract-Identity Discrepancy Resolution — Decision Protocol v0.1

## Document control

- **programme_id:** `OVC-MG-EI-WP1-CONTRACT-IDENTITY-DISCREPANCY-v0.1`
- **plan_id:** `OVC-MG-EI-WP1-CID-DECISION-PROTOCOL-0.1`
- **packet_id:** `EI-WP1-CID-WP0`
- **gate_id:** `EI-WP1-CID-G0`
- **repository:** `owenguobadia24s-collab/ovc-replay`
- **baseline_main:** `22c5ede9c6e7ccdeba26ea53e7a83890170b10dd`
- **branch:** `governance/mg-ei-wp1-contract-identity-discrepancy-v1`
- **status:** `GATE_READY`
- **authority_effect:** `NONE` until an explicit operator decision authorises the forward supersession.
- **trigger:** `PYT-WP2-BLOCK-001 FROZEN_CONTRACT_IDENTITY_DISCREPANCY`

## 0. Purpose

Resolve one identity-bearing contract discrepancy without rewriting historical evidence. The existing EI-WP1 forward adapter surface declares a malformed 62-character value as `binding_sha256`, while earlier governing evidence and accepted replay artifacts bind the same `C2VNEXT.JUNE.DISCOVERY.INPUT.v1` identity to a reproducible 64-character SHA-256.

This protocol determines which identity is authoritative, defines the preservation/supersession rule, and stops at an operator-required gate before any material change to the frozen EI-WP1 contract surface.

## 1. Finding

**Finding: `AUTHORITATIVE_64_CHARACTER_DIGEST_EXISTS`.**

The authoritative binding identity for `C2VNEXT.JUNE.DISCOVERY.INPUT.v1` is:

`126a703b89bfef8fc60a4beb1248b20b424621334c8fff254c122555e44663f8`

The malformed historical EI-WP0/EI-WP1 transcription is:

`126a703b89bf8fc60a4beb1248b20b424621334c8fff254c122555e44663f8`

The malformed value is 62 characters. It is not a valid SHA-256. The authoritative value is 64 lowercase hexadecimal characters and differs by the omitted pair `ef` immediately after the prefix `126a703b89bf`.

## 2. Evidence basis

The 64-character identity is independently preserved by:

1. `docs/plans/OVC_MARKET_GRAMMAR_EMPIRICAL_INTEGRATION_JUNE_IMPLEMENTATION_PLAN_v0_1.md`, section 3, which freezes the exact EI programme binding SHA-256 as `126a703b89bfef8fc60a4beb1248b20b424621334c8fff254c122555e44663f8`.
2. `docs/releases/c2e-c2g-c2p-market-grammar-v0-1/mg-d0/MG_D0_VERIFIED_SHADOW_EVIDENCE_LOCK.json`, a PASS evidence lock recording the same binding ID and 64-character binding SHA-256, plus binding raw SHA-256 `b4c4785087396fd445a749382899f0e441a1d9947c39b59e20f7e920b5ccbed2`.
3. `docs/releases/c2e-c2g-c2p-market-grammar-v0-1/mg-wp0/MG_WP0_EXTERNAL_ARTIFACT_INVENTORY.json`, a `READ_ONLY_HASH_LOCK` recording the same 64-character binding identity and the same raw binding hash.
4. `registries/implementation/c2e_v0_2/run_authority/C2E2_SOURCE_RUN_MANIFEST_JUNE_v0_1.json`, which authorises only the exact source population and records `input_binding_sha256=126a703b89bfef8fc60a4beb1248b20b424621334c8fff254c122555e44663f8`.
5. Google Drive accepted run-001 `output-manifest.json` file id `1iW7a9eaHIcc_k1-aVTDTaHrVCr12Hb7Q`, whose raw bytes hash to `2808729f929412f56ad3061b0cbbcd42bdb277bfc779cd1885f605584295a693` exactly as the repository MG-WP0 inventory declares; its decoded `binding_sha256` is `126a703b89bfef8fc60a4beb1248b20b424621334c8fff254c122555e44663f8`.
6. `src/ovc/opt_b/c2_vnext/full_replay.py`, which defines `binding_hash(value)` as SHA-256 of the canonical binding object with `binding_sha256` removed and validates exact equality fail-closed.

Together these are sufficient to treat the 64-character value as an already-existing accepted identity, not a newly invented digest.

## 3. Discrepancy classification

Classification: `FORWARD_TRANSCRIPTION_TRUNCATION_OF_EXISTING_IDENTITY`.

The error was introduced downstream of the accepted replay evidence when the `ef` pair was omitted. The 62-character string is therefore historical evidence of a transcription defect; it is not a second valid hash and must not be padded, guessed, reinterpreted as another digest algorithm, or silently accepted by weakening validation.

## 4. Preservation rule

Historical artifacts containing the 62-character string remain immutable court-record evidence. They must not be rewritten in place under their existing version identities.

The forward correction, if approved, must use explicit versioned supersession/correspondence:

- retain `MG_EI_WP1_REVISED_C2_SOURCE_ADAPTER_CONTRACT_v0_1.md` unchanged;
- create `MG_EI_WP1_REVISED_C2_SOURCE_ADAPTER_CONTRACT_v0_2.md` with the authoritative 64-character binding;
- retain historical v0.1 fixture/registry identities unchanged;
- create v0.2 fixture/registry identities for forward execution;
- add a correspondence record from the malformed historical value to the authoritative binding identity with relationship `TRANSCRIPTION_CORRECTION_NO_SOURCE_IDENTITY_CHANGE`;
- update forward runtime consumers to the v0.2 contract only;
- retain the same `binding_id=C2VNEXT.JUNE.DISCOVERY.INPUT.v1`; do not create a new market-data/source identity because the accepted underlying binding is unchanged.

## 5. Proposed forward packet after approval

`EI-WP1-CID-WP1 — VERSIONED_SUPERSESSION`

Required outputs:

- v0.2 EI-WP1 source-adapter contract;
- v0.2 fixture and implementation registry;
- correspondence/supersession ledger;
- runtime adapter binding to the authoritative 64-character digest;
- explicit tests that v0.1 remains historical and invalid for SHA-256 execution, while v0.2 accepts only the exact authoritative digest;
- regression proof that source slice, logical population, integrated package, instrument, clocks, sides, chronology and all authority denials are unchanged;
- targeted EI-WP1/EI-WP2 tests;
- PYT-WP2 unified pytest re-entry only after the supersession packet is merged.

The packet must not rewrite source data, alter selectors, promote families/semantics/candidates, open Validation, publish a new release, or grant probability/risk/exposure/execution authority.

## 6. Gate

`EI-WP1-CID-G0` is **OPERATOR_REQUIRED** because the proposed action materially supersedes a frozen identity-bearing contract.

Allowed decisions:

- `PASS_SUPERSEDE` — approve the v0.2 forward correction exactly as defined above.
- `DEFER` — preserve the blocker and take no forward action.
- `BLOCK` — reject the 64-character authority finding and require additional authoritative source evidence.
- `QUARANTINE` — quarantine EI-WP1 forward execution while preserving all evidence.
- `SUPERSEDE` — replace this decision protocol with a separately specified resolution.

No code, contract, fixture or registry correction may be executed until the operator decision is materialised.

## 7. Rollback

Before operator approval, rollback is deletion/supersession of this decision-only branch/PR; no frozen artifact has changed.

After a future `PASS_SUPERSEDE`, rollback must disable the v0.2 forward adapter surface and return consumers to a blocked state. It must never reactivate the malformed 62-character value as a valid SHA-256 and must never rewrite historical v0.1 evidence.
