# A2-G4 — Remote publication verification and authority review

## Decision

**PASS.** The three exact A2-G3 OPT-A v2 role releases are published in the immutable Cloudflare R2 canonical namespace and have passed complete remote byte readback verification.

A2-G4 changes release availability only. It does not activate an OPT-A selector, consume Validation, open an active OPT-A-to-OPT-B handoff, or create market, probability, exposure, trading or execution authority.

## Reviewed execution

- WP6 pull request: `#12`
- WP6 publication branch head: `582eaaa4f844422270095bea90dd3488852762cf`
- WP6 workflow execution commit: `904a8fa4c6c69a6785bad1e428e0443ddfe8479d`
- WP6 merge commit: `8f0dd49e489b531df8998b4fc1575d6fb11317d1`
- WP6 workflow run: `30181995980`
- Publication-report artifact: `8625889699`
- Artifact digest: `sha256:67f9ea95026c60a6c42446974a887f9a900a2fd0809ee09a685d7ed65b827d3f`
- Publication-report self-hash: `b6f482d5f94a266593ad9a0012925a9a9389764206605f731e65cbb66e3f6d4a`

The operator review independently confirmed that the downloaded artifact ZIP matched the GitHub artifact digest, the compact report self-hash recomputed exactly, every remote manifest matched its deterministic local manifest, and all three manifest diff files were empty.

## Published releases

| Role | Release | Manifest | Files | Bytes | Result |
|---|---|---|---:|---:|---|
| Discovery | `OPT-A.GBPUSD.DISCOVERY.2021_2023.v2` | `MANIFEST.OPT-A.GBPUSD.DISCOVERY.2021_2023.v2.r2` | 293 | 155,632,392 | `REMOTE_VERIFIED` |
| Development | `OPT-A.GBPUSD.DEVELOPMENT.2024.v2` | `MANIFEST.OPT-A.GBPUSD.DEVELOPMENT.2024.v2.r2` | 101 | 52,762,768 | `REMOTE_VERIFIED` |
| Validation — locked | `OPT-A.GBPUSD.VALIDATION.2025.v2` | `MANIFEST.OPT-A.GBPUSD.VALIDATION.2025.v2.r2` | 101 | 52,304,577 | `REMOTE_VERIFIED / LOCKED_UNCONSUMED` |

The remote manifests have SHA-256 identities:

- Discovery: `0cbcafa9421449574b61bfeec24f634de99cbbbc6e7a53d09ace8f702182ab8c`
- Development: `25e1be8a7edb0e96017c45bf35f4e788345f94b22a8ed9bb0874c86338ba64cc`
- Validation: `9d855d4c7dda01182a574cba96761c2f545266580307b2e2bc764af6d933b877`

## Assurance results

- Exact A2-G3 artifact binding: `PASS`
- Manifest-bound publication approvals: `PASS`
- Immutable payload-first upload: `PASS`
- Manifest-last completion: `PASS`
- Remote manifest identity: `PASS`
- Full payload byte readback: `PASS`
- Empty local-versus-remote manifest diffs: `PASS`
- Validation default-deny lock: `PASS`
- Selector non-mutation: `PASS`
- Quarantine disposition preservation: `PASS`

## Quarantine disposition

The **21,410** side-specific derived-bucket records, representing **10,705** side-independent clock-time locations, remain governed by:

`RETAIN_TRACE_AND_EXCLUDE_FROM_ACCEPTED_OBSERVATIONS`

Publication did not fill, repair, substitute, promote or erase any quarantined bucket.

## Authority delta

After A2-G4:

- R2 publication: `COMPLETE_REMOTE_VERIFIED`
- Release lifecycle: `REMOTE_VERIFIED`
- Release authority: `SHADOW_NOT_SELECTED`
- OPT-A selector set: `NONE`
- Validation consumption: `LOCKED_UNCONSUMED`
- Active OPT-A-to-OPT-B handoff: `NONE`
- Market authority: `NONE`
- Probability, exposure, trading and execution: `DENIED`

The exact manifest IDs and remote-verification review record may now be used in a separately reviewed activation proposal. Publication itself is not activation.

## Rollback and immutability

The verified remote objects remain immutable and are not deleted or overwritten. Rollback before activation is simply to retain all selectors at `NONE`. Historical v1 reactivation remains prohibited.

## Next gate

`A2-G5 — selector-set activation`

A2-G5 must independently verify the exact three remote manifests, perform an atomic role-selector proposal, preserve the Validation lock, verify rollback to `NONE`, and record an explicit operator activation decision.
