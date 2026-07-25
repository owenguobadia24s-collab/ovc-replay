# A2-G2 — Operator Review of Observation Construction

## Decision

**PASS.** The remediated WP5 discovery, development and locked-validation workspaces are admissible inputs to the bounded `A2-G3 — role release freeze` packet.

This decision approves observation construction and the explicit quarantine disposition only. It does not freeze a release, publish to R2, activate a selector, consume validation, enable the OPT-A-to-OPT-B handoff or grant market authority.

## Reviewed baseline

- Programme: `OVC-OPT-A-V2-IMPLEMENTATION-PLAN-0.2`
- Gate: `A2-G2`
- Main baseline: `bce2499dff255076b2fe297035d8923f4a21776c`
- Review execution commit: `8d62471c3a9d81e46d5193e82d3b64497e5b3853`
- Canonical test workflow: `30178480639` — PASS
- Role-workspace workflow: `30178480623` — PASS

## Review method

The operator review independently downloaded and expanded the three remediated role-workspace artifacts and compact report. It verified:

- GitHub artifact ZIP SHA-256 against the Actions artifact digest;
- canonical workspace-manifest self-hash;
- every emitted observation object's byte size and SHA-256;
- exact role, source-object and observation-object cardinality;
- portable, workspace-relative observation paths and artifact-root-relative provider paths;
- unique deterministic quarantine bucket IDs;
- exact missing and unexpected timestamp arrays for every quarantined bucket;
- agreement between expected, observed, missing and unexpected counts;
- BID/ASK quarantine symmetry;
- integer coverage totals and acceptance rates;
- validation default deny and unchanged authority boundaries.

Observed review violations after remediation: **0**.

## Reviewed artifacts

| Role | Artifact ID | SHA-256 | Source objects | Observation objects | Manifest SHA-256 |
|---|---:|---|---:|---:|---|
| Discovery | `8624894577` | `402babcbbe26e9f4297e0526183ce44d67f879bd7d2554c6132163599e0cae5c` | 144 | 288 | `f1ef621bce4a098a80d2cb309ae6f9cba2fcd177e71ce1ac98614f826e0f9a71` |
| Development | `8624894979` | `6897377b47b645c53678eedea1d8e5e1802ebc18b7cfe84a21e604374e4ac2a6` | 48 | 96 | `fa527f01fc0db621cbcddf2fe4bbe8f697e54c9af238e56e85f2a4da0140b1c2` |
| Validation — locked | `8624895364` | `d48a19ba123f007029f9fe226fd31bf8e88ce17eafdf03a4daa2bfba7d5163fb` | 48 | 96 | `9e92e479b7d39e6669681659d0acf98b1d686d0dc66bfe2e8558d742aaa13514` |
| Compact report | `8624895466` | `7140eb871f0d5007ae45a302b5b443644323be95cd44352d083b7683bd01d752` | — | — | — |

## Observation coverage

Acceptance rates below are calculated independently per side. BID and ASK counts are identical.

| Role | Clock | Accepted per side | Quarantined per side | Candidate per side | Acceptance |
|---|---|---:|---:|---:|---:|
| Discovery | M1 | 1,116,170 | 0 | 1,116,170 | 100.0000% |
| Discovery | 15M | 71,982 | 2,828 | 74,810 | 96.2197% |
| Discovery | H1_M1_DERIVED | 16,969 | 1,734 | 18,703 | 90.7287% |
| Discovery | 2H_A_L | 7,964 | 1,490 | 9,454 | 84.2394% |
| Development | M1 | 372,461 | 0 | 372,461 | 100.0000% |
| Development | 15M | 23,853 | 1,143 | 24,996 | 95.4272% |
| Development | H1_M1_DERIVED | 5,538 | 712 | 6,250 | 88.6080% |
| Development | 2H_A_L | 2,583 | 576 | 3,159 | 81.7663% |
| Validation — locked | M1 | 371,095 | 0 | 371,095 | 100.0000% |
| Validation — locked | 15M | 23,827 | 1,073 | 24,900 | 95.6907% |
| Validation — locked | H1_M1_DERIVED | 5,589 | 637 | 6,226 | 89.7687% |
| Validation — locked | 2H_A_L | 2,635 | 512 | 3,147 | 83.7305% |

## Quarantine disposition

The workspaces contain **21,410 side-specific quarantined derived buckets**:

- discovery: **12,104**;
- development: **4,862**;
- validation: **4,444**.

All carry the reason `INCOMPLETE_OR_NONCONTIGUOUS_M1_BUCKET`. They represent **10,705 clock-time bucket locations**, each recorded consistently on both BID and ASK chains.

Disposition: `RETAIN_TRACE_AND_EXCLUDE_FROM_ACCEPTED_OBSERVATIONS`.

For every quarantined bucket:

1. retain the quarantine record, bucket ID, source-object lineage and exact missing/unexpected timestamp set;
2. exclude the bucket from accepted 15M, H1_M1_DERIVED and 2H_A_L observations;
3. prohibit interpolation, fill, synthetic candles, provider-native H1 substitution, cross-side substitution and manual repair;
4. prohibit its use as an OPT-B parent, selector input or release-authoritative observation;
5. permit A2-G3 to package the quarantine ledger alongside accepted outputs without promoting quarantined rows;
6. preserve the role boundary, with validation remaining `LOCKED_UNCONSUMED`.

The quarantine population is therefore a lawful, retained statement of source-chain incompleteness, not a failed release and not accepted market truth at the affected derived clocks.

## Authority delta

A2-G2 now authorises preparation and execution of the bounded A2-G3 role-release freeze packet against the reviewed artifact identities above.

Still denied:

- Cloudflare R2 publication;
- selector activation;
- validation consumption;
- active OPT-A-to-OPT-B handoff;
- OPT-B/C/D market claims;
- probability, exposure, trading and execution.

## Expiry and rebuild rule

The three role-workspace artifacts expire on 24 August 2026. A2-G3 must either use these exact artifact IDs and digests before expiry or deterministically rebuild from the verified WP4 source objects under the reviewed implementation commit and re-run this identity review. Artifact expiry does not authorise substitution or relaxed verification.

## Final gate result

`A2-G2: PASS`

Next bounded gate: `A2-G3 — role release freeze`.
