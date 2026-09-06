# RRSCG Core WP0 Successor — Exact Source Recovery & Binding Report v0.1

**Packet:** `RRSCG-CORE-WP0-SOURCE-RECOVERY-AND-EXACT-BINDING-SUCCESSOR`  
**Baseline:** `01621f29cab89d086517b5dbaf6f4fa9f1bbcf7c`  
**Authority effect:** `NONE_SOURCE_BINDING_ONLY`  
**Disposition:** `PASS_EXACT_SOURCE_BINDING / OPERATOR_GATE_READY_AFTER_INTEGRATION`

## Recovery event

The operator supplied the exact historical RRSCG source archives that the integrated WP0 blocker had identified as unavailable. The archives were treated as external evidence in accordance with `artifacts/README.md`; they were not rewritten, recompressed or committed as duplicate engine ZIPs.

## R2

`OVC_EML_GRAMMAR_0003_RRSCG_AlgorithmPack_v0_1_REVISED_2_FREEZE_CANDIDATE.zip` materialised with SHA-256:

`5426cd9340c93a2aff0f5c8f3093f9db876647d1790aaa82da3e444a4f3029b5`

This exactly equals the preserved immutable R2 identity. All 75 entries in the archive's `SHA256SUMS.txt` verified and the package's 14 tests passed on the materialised bytes without source modification.

## D9

The exact D9 release bundle materialised with SHA-256:

`5898709a7c34a413d775ca1cbb88ef0851809851573e504386c5176b7328b1e5`

Its nested D9 freeze candidate hashes to the preserved D9 package identity:

`edbb3e0448845eee375dbefdf2f33fe2d6df3c1ffd4605b28dc117576d7ea398`

Its release binding hashes to the preserved identity:

`b4fea0c43622f7b7c689136be4844a406db4027c218a8a604eaacde17ae565c5`

The separately materialised `OVC_EML_GRAMMAR_0003_RRSCG_D9_IMPLEMENTATION_0001.zip` hashes exactly to:

`15c4f3c5bca53e40894c54c8d4cffdca2675a8f62a537efe1b2533efb09bb23a`

All 29 internal `SHA256SUMS` entries verified. Its vendored R2, D9 package and D9 release-binding hashes independently reproduce the same preserved identities.

## D10

The D10 exact release bundle materialised with SHA-256:

`092bf144b38f84a43946d36a15d0905c2bce7f51e7ca815e6814eae361d1ad67`

The full D10 freeze-candidate package identity is now recovered as:

`6b58e9edbb16dd5f8e6f182d0af82c46279a28fc030b4d560bcd69635729515f`

This satisfies the previously preserved `6b58e...` prefix. The same full identity is independently present in the D10 exact-release manifest, fresh exact-byte review, final algorithm qualification receipt and release binding. The separately supplied D10 freeze-candidate archive is byte-identical to the candidate nested inside the exact release bundle.

The D10 release evidence also binds its exact D9 parent to `edbb3e...` and immutable R2 parent to `5426cd...`, producing a consistent R2 → D9 → D10 source chain.

## G0 disposition

All load-bearing RRSCG source identities selected by the ratified core plan are now `BOUND_EXACT`; D10's previously incomplete full identity is recovered; no source contradiction was found. `RRSCG-CORE-G0-SOURCE-BINDING` therefore qualifies for delegated `PASS`, conditional on exact-final repository assurance and lawful integration of this record.

This PASS changes no historical scientific claim, performs no algorithm reconstruction and grants no implementation or persistent architecture authority.

## Reserved boundary

After lawful integration, execution must stop at:

`LSIAC-G-RRSCG-CORE-ACCESSION-AUTHORITY_AFTER_WP0_SOURCE_BINDING`

The requested operator grant is limited to construction and conformance testing of the versioned **inactive** RRSCG Research Operations capability under the ratified core plan. Without explicit operator approval, WP1 implementation remains prohibited.
