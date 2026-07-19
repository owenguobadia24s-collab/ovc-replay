# Import provenance

This repository was assembled on 2026-07-19 from the durable OVC release
artifacts after the original transient workspace had been cleared.

## Canonical executable tree

The source, scripts, contracts, and tests were restored from:

| Package | Role | SHA-256 |
| --- | --- | --- |
| `OVC_OPT_D_VALIDATION_ENGINE_v0_1.zip` | Cumulative A-D engine through untouched validation | `9383a6d9c9a1db289f263c99d912083922349116881af41a22849f99e79f3ae8` |
| `OVC_OPT_D_ROBUSTNESS_PAPER_GATE_ENGINE_v0_1.zip` | Final robustness and paper-gate overlay | `c56bf984cf5fdd35e616ef6584f3548a37405099c47ae572a686e3f3bceb279d` |

The overlay extends the cumulative engine with `robustness.py`, four runner and
validator scripts, two contracts, one test module, and updated public exports.

## Historical releases

Compact project-control artifacts were extracted from the saved OPT-A, OPT-B,
OPT-C, and OPT-D release packages. The final Git boundary excludes every OHLCV
or market CSV, raw provider record, generated state/outcome stream, audit/evidence
ledger, cache, and opaque release ZIP. Committed history is limited to Markdown,
JSON, non-market inventory CSVs, text/checksums, and compact semantic registries.

The resulting import contains 21 release-history directories. Their canonical
manifests provide filename and hash discovery for omitted external artifacts,
including raw minute data, canonical bar tables, and exhaustive replay streams.

## Import validation

- 107/107 unit and contract tests passed.
- Every committed JSON document parsed successfully.
- Every retained compressed registry passed integrity validation.
- No committed file exceeds 10 MiB.
- The repository contains no detected GitHub or OpenAI credential pattern.

This import reorganizes files but does not rewrite sealed release manifests or
claim that compact history directories are self-contained replay bundles.
