# ASOCSI-WP1 Source Qualification Contract v0.1

Status: `FROZEN_BY_G_SOURCE_AFTER_EXACT_HEAD_ASSURANCE`

Programme: `OVC-ASOCS-6M-v0.1`  
Plan: `OVC-ASOCS-CONFORMANCE-SCIENTIFIC-PREREGISTRATION-IMPLEMENTATION-PLAN-0.1-R1` / `0.1_REVISED_1`

## Authority

This contract consumes only the exact local audit source with SHA-256 `210233ec5761bf82998172832bb554ddf10dfeb3099f6bc6488d5bb0f6bec4f2` under `ASOCS_AUDIT_ONLY_EXACT_HASH_LOCAL_CONSUMPTION`. It does not create an OPT-A release, activate Darwinex, assign a Discovery/Development/Validation role, mutate a selector, change C1/C2/C2E semantics, activate EC1, publish evidence, or grant probability/risk/execution authority.

## Literal parser

- UTF-8 is decoded strictly.
- Header is exactly `Date,Time,Open,High,Low,Close,Volume`.
- `Date` is exactly eight ASCII digits in `YYYYMMDD` form.
- `Time` is exactly `HH:MM:SS`.
- Date and Time are concatenated as `Date + " " + Time` and parsed without timezone attachment or conversion.
- OHLC and Volume use `decimal.Decimal`; localized comma decimals, whitespace coercion, NaN and infinity are rejected.
- OHLC must satisfy `Low <= Open <= High`, `Low <= Close <= High`, positive OHLC and nonnegative Volume.
- Missing cells, duplicate timestamps and non-monotonic ordering fail closed.
- Source bytes are never repaired, normalized, interpolated, side-reconstructed or timezone-shifted.

## Provenance freeze

Only supplied/export evidence may resolve provenance. For the bound source:

- provider label `DARWINEX`: `DECLARED` from supplied artifact identity and ratified ASOCS design;
- price side: `UNRESOLVED_SINGLE_STREAM` / `UNRESOLVED`;
- timestamp timezone: `SOURCE_TIMEZONE_UNRESOLVED` / `UNRESOLVED`;
- session metadata: `NONE_SUPPLIED`;
- H1 2026 role: `ASOCS_AUDIT_OUT_OF_ROLE_H1_2026`.

Inference is never promoted to exact provenance by assertion.

## Claim-class firewall

Because exact side and timestamp/clock provenance do not resolve, WP1 freezes `ASOCS_SINGLE_STREAM_MORPHOLOGY_COHERENCE`. Exact active-interface claims are denied. Each active construct is recorded separately as `NOT_EVALUABLE_EXACT_ACTIVE_INTERFACE`; WP4 may later prove or fail-close a non-authoritative morphology-compatible adapter under the already-approved plan. This WP1 decision does not itself prove morphology compatibility.

## Gap boundary

WP1 defines the `ASOCSSourceGap` schema and records target adjacent-gap diagnostics. WP2 owns the complete conservative gap ledger and any classification beyond literal non-contiguity. No gap is called a market closure without exact provenance.

## Acceptance

1. Exact source SHA-256, byte size `11,048,144`, row count `186,145`, exact header and month counts reproduce.
2. No parse, missing-cell, OHLC envelope, numeric-domain, duplicate or non-monotonic failures occur.
3. Target count is `183,408`; pre-context `1,319`; post-context `1,418`; target gaps >1 minute are `377`, shortest 2 minutes and longest 2,894 minutes.
4. Side/timezone uncertainty is explicit and representable without fabrication.
5. Claim class and per-construct exact-interface evaluability freeze before any target structural replay.
6. H1 2026 remains audit-only and unavailable to EC1 or role selectors.

## Rollback

Forward-supersede this WP1 qualification generation only. Preserve source hash, raw bytes, G0 authority, provenance uncertainty, prior decisions and all historical evidence.
