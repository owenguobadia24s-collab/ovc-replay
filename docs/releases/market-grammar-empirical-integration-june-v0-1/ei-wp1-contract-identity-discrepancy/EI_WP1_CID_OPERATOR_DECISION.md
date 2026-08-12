# EI-WP1-CID-G0 — Operator Decision

**Programme:** `OVC-MG-EI-WP1-CONTRACT-IDENTITY-DISCREPANCY-v0.1`  
**Gate:** `EI-WP1-CID-G0`  
**Status:** `GATE_READY / OPERATOR_REQUIRED`  
**Baseline:** `22c5ede9c6e7ccdeba26ea53e7a83890170b10dd`

## Decision finding

The evidence packet determines that an authoritative reproducible 64-character SHA-256 **does exist** for `C2VNEXT.JUNE.DISCOVERY.INPUT.v1`:

`126a703b89bfef8fc60a4beb1248b20b424621334c8fff254c122555e44663f8`

The downstream EI-WP0/EI-WP1 value:

`126a703b89bf8fc60a4beb1248b20b424621334c8fff254c122555e44663f8`

is a 62-character transcription truncation, specifically missing `ef` after `126a703b89bf`. It is not a second valid digest.

The accepted run-001 Drive output manifest has raw SHA-256 `2808729f929412f56ad3061b0cbbcd42bdb277bfc779cd1885f605584295a693`, matching the repository's frozen MG-WP0 inventory exactly, and its decoded `binding_sha256` is the authoritative 64-character value.

## Recommended decision

`PASS_SUPERSEDE`

Approve a **forward, versioned** EI-WP1 v0.2 correction while preserving all v0.1 artifacts containing the malformed value as historical evidence.

Approval authorises only:

- a new v0.2 EI-WP1 contract/fixture/registry/correspondence surface;
- forward runtime migration to that v0.2 surface;
- deterministic tests and QA needed to prove the correction;
- subsequent resumption of PYT-WP2 after the supersession packet is lawfully merged.

Approval does **not** authorise provider intake, source identity replacement, selector change, Active Discovery/Development/Validation, family/semantic/candidate/theory promotion, publication, probability, risk, exposure or execution authority.

## Operator decision

`PENDING`

Allowed values: `PASS_SUPERSEDE`, `DEFER`, `BLOCK`, `QUARANTINE`, `SUPERSEDE`.

Exact approval command:

`OVC APPROVE EI-WP1-CID-G0 PASS_SUPERSEDE`
