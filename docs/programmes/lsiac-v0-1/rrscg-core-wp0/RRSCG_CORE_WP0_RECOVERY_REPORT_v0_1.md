# RRSCG Core WP0 — Source Recovery & Exact Binding Report v0.1

**Packet:** `RRSCG-CORE-WP0-SOURCE-RECOVERY-AND-EXACT-BINDING`  
**Baseline:** `8dd38fede57a4f92603d9676c699cee7d8f5f53f`  
**Authority effect:** `NONE_SOURCE_RECOVERY_AND_BINDING_ONLY`  
**Disposition:** `BLOCK / EXACT_SOURCE_BYTES_NOT_CURRENTLY_MATERIALISABLE`

## Purpose

WP0 attempts to recover and bind the exact algorithm-defining bytes for the minimal RRSCG repository core selected by LSIAC-R2: immutable R2 continuation-constraint kernel, D9 constraint-state geometry/kinematics machinery, and the narrow D10 reducer subcomponent.

This packet does **not** implement RRSCG. It does not infer source code from reports, result packs, behavioral outputs, journal descriptions or remembered semantics.

## Recovery outcome

### R2

Historical evidence fixes the parent algorithm as `OVC-EML-GRAMMAR-0003-RRSCG-ALGORITHM-0.1-R2` with exact package SHA-256 `5426cd9340c93a2aff0f5c8f3093f9db876647d1790aaa82da3e444a4f3029b5`. The source-bound journal records the exact ZIP, 14/14 package tests and 22/22 independent checks. The exact archive bytes are not currently materialisable from repository or accessible source-library surfaces.

### D9

Historical evidence fixes the D9 package SHA-256 as `edbb3e0448845eee375dbefdf2f33fe2d6df3c1ffd4605b28dc117576d7ea398` and Implementation 0001 source-package SHA-256 as `15c4f3c5bca53e40894c54c8d4cffdca2675a8f62a537efe1b2533efb09bb23a`.

This is stronger than a journal-only assertion: an exact D9 intake record states that the expected and uploaded Implementation 0001 archive hashes matched, all 29/29 SHA256SUMS entries verified, and the six implementation tests passed. Therefore D9 is classified as **historically materialised and exact-byte verified, but currently unretrievable**. That condition does not permit reconstruction or implementation from the surviving descriptions.

### D10

The LSIAC source passports preserve D10's fresh successor-reducer comparison, promotion eligibility, exact-byte review and reducer-only forward supersession. Surviving indexed evidence exposes only a package hash prefix `6b58e...`; the full expected package identity and exact algorithm-defining bytes are not currently materialised. D10 therefore remains fail-closed.

## Repository/archive search finding

Current `main` contains the LSIAC accession records but no exact RRSCG core source implementation. The repository's 2026-08-31 Project Source Retirement Archive is not a hidden RRSCG source store: its commit records 23 unrelated project-source documents and explicitly states that exact binary bytes were not committed and external-artifact bindings remained `UNBOUND`.

## Fail-closed decision

WP0 cannot lawfully declare an exact binding PASS. The following remain blocked:

- repository-native RRSCG implementation;
- conformance execution using reconstructed code;
- persistent RRSCG canonical-capability accession;
- D9 observer-faculty accession.

This is a **source-materialisation blocker**, not a scientific rejection. Historical RRSCG results, reviews and exactness attestations remain preserved at their existing standing.

## Lawful resume condition

A source custodian or operator must materialise the exact R2, D9 and D10 algorithm-defining bytes. WP0 then resumes by hashing those bytes, comparing them to the preserved identities, recovering D10's full expected package identity, and verifying exact contents without semantic amendment.

Only if that successor WP0 binding passes may OVC reach the separately operator-reserved gate `LSIAC-G-RRSCG-CORE-ACCESSION-AUTHORITY_AFTER_WP0_SOURCE_BINDING`.
