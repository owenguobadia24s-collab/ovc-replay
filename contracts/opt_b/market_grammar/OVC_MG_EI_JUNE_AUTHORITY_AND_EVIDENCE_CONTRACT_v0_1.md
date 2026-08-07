# OVC MG Empirical Integration June — Authority and Evidence Contract v0.1

## Authority

This contract is governed by the explicit operator `PASS` at `MG-WP10`. It authorises only bounded empirical integration over the already accepted June GBPUSD evidence under inactive, noncanonical `SHADOW_EXPERIMENT` authority.

## Required parent records

- `docs/releases/c2e-c2g-c2p-market-grammar-v0-1/mg-wp10/MG_WP10_OPERATOR_DECISION.json`
- `docs/releases/c2e-c2g-c2p-market-grammar-v0-1/mg-wp10/MG_WP10_POST_MERGE_RECEIPT.json`
- `docs/releases/c2e-c2g-c2p-market-grammar-v0-1/mg-wp0/MG_WP0_EXTERNAL_ARTIFACT_INVENTORY.json`
- `registries/opt_b/market_grammar/MG_C2G_SENSITIVITY_PACK_REGISTRY_v0_1.json`
- all completed MG-WP1 through MG-WP9 contracts, implementations, QA and decisions.

## Admissible source rule

A source object is admissible only when name, byte size and SHA-256 all match the frozen evidence lock. The four accepted source files are immutable inputs. Retrieval from their existing Google Drive evidence folder is read-only artifact recovery, not provider intake. Any missing file, changed byte count or hash mismatch is a blocking `EVIDENCE_IDENTITY_MISMATCH`.

## External source identities

Source folder: `RPS.DUKASCOPY.GBPUSD.20260530_20260703.v1` (`1x5v1UV3UdMzIwtgmSzTNreaPqzw0jDJm`).

- M1 BID Drive ID `1YNe_JqSmxkI1YhLvTiFfQO-YtQQ8EtAG`, SHA-256 `d704b3bac2d51e839505ee5bc2ba7589ce44310353bbb6a464a1850fe1af5789`, 2,164,613 bytes.
- M1 ASK Drive ID `1TbNgAAnJxRYEkDjpeWMtslSPs5kSwITQ`, SHA-256 `bc643e62ebbc35940f93aaaaead147b6f9170b1a030a473436b2dc84d6992057`, 2,165,135 bytes.
- H1 BID Drive ID `1h46pG1_hQDcSJiles_M1qLAkJLS84zXT`, SHA-256 `b6116ea784be785089e881c8b8a69c8d5d202cb57f3d058f71d159071bd51c24`, 35,893 bytes.
- H1 ASK Drive ID `1Vb2qwO8Z2MDOKF5uXGnBhCcoZa89G0MH`, SHA-256 `a25dcf89cb35afbbc6fb722e7f379511ceb83af0a5f1fc1b32c94e8adc304e5d`, 36,025 bytes.

## Read boundary

EI code may read only:
- the exact accepted external source objects and existing accepted replay/binding artifacts;
- repository contracts, schemas, registries and completed shadow evidence required by MG-WP10;
- current/prior records necessary for deterministic C2E/C2G processing at or before the build cutoff.

It must reject:
- unknown source identities;
- new provider downloads;
- any future/outcome/return/MFE/MAE/probability/risk/exposure/execution field;
- runtime path, machine, user or wall-clock metadata as a structural matching feature;
- hidden threshold or sensitivity overrides;
- cross-side synthesis or clocks outside 15M and `2H_A_L`.

## Two boundary replacements

`EI-WP1` replaces the synthetic MG-WP8 `c2_records` input with a read-only real revised-C2 adapter bound to the accepted package/population.

`EI-WP2` replaces the synthetic MG-WP8 `state_structural_features` input with a deterministic five-axis projection over LOCATION, MOTION, ORGANISATION, INTERACTION and QUALITY. Missing/uncomputable evidence remains explicit; it may never be silently neutralised.

## Output authority

All output is replaceable empirical evidence with:
- `authority_state=SHADOW_EXPERIMENT`;
- `canonical=false`;
- `published=false`;
- `promotion_authority=NONE`;
- no selector writes.

## Stop boundary

The programme must stop before any canonical selection, family/variant/rule/candidate/grammar/semantic promotion, selector activation/replacement, publication/new release identity, C3 handoff, Active Discovery/Development/Validation, probability, risk, exposure or execution authority.
