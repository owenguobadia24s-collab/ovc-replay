# EI-WP1-CID-G0 — Operator Decision

**Programme:** `OVC-MG-EI-WP1-CONTRACT-IDENTITY-DISCREPANCY-v0.1`  
**Gate:** `EI-WP1-CID-G0`  
**Status:** `APPROVED`  
**Decision:** `PASS_SUPERSEDE`  
**Approved candidate:** `4e06beaf04c7dae6b27bd576b08ca7a78ade2a56`  
**Operator command:** `OVC APPROVE EI-WP1-CID-G0`  
**Approved at:** `2026-08-12T20:06:00+01:00`

## Decision finding

The evidence packet determines that an authoritative reproducible 64-character SHA-256 exists for `C2VNEXT.JUNE.DISCOVERY.INPUT.v1`:

`126a703b89bfef8fc60a4beb1248b20b424621334c8fff254c122555e44663f8`

The downstream EI-WP0/EI-WP1 value:

`126a703b89bf8fc60a4beb1248b20b424621334c8fff254c122555e44663f8`

is a 62-character transcription truncation, specifically missing `ef` after `126a703b89bf`. It is not a second valid digest.

The accepted run-001 Drive output manifest has raw SHA-256 `2808729f929412f56ad3061b0cbbcd42bdb277bfc779cd1885f605584295a693`, matching the repository's frozen MG-WP0 inventory exactly, and its decoded `binding_sha256` is the authoritative 64-character value.

## Approved authority delta

`PASS_SUPERSEDE` authorises a forward, versioned EI-WP1 v0.2 correction while preserving all v0.1 artifacts containing the malformed value as historical evidence.

Approval authorises only:

- a new v0.2 EI-WP1 contract/fixture/registry/correspondence surface;
- forward runtime migration to that v0.2 surface;
- deterministic tests and QA needed to prove the correction;
- subsequent resumption of PYT-WP2 after the supersession packet is lawfully merged.

Approval does not authorise provider intake, source identity replacement, selector change, Active Discovery/Development/Validation, family/semantic/candidate/theory promotion, publication, probability, risk, exposure or execution authority.

## Rollback

Disable or supersede the v0.2 forward surface and return consumers to a blocked state while preserving this operator decision and all v0.1 historical evidence. The malformed 62-character value must never be reactivated as a valid SHA-256.

## Next

Execute `EI-WP1-CID-WP1 — VERSIONED_SUPERSESSION`, run targeted and repository assurance, merge if eligible, then resume `PYT-WP2` from current main.
