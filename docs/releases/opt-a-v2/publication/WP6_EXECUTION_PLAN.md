# WP6 — OPT-A v2 canonical R2 publication and full-byte remote verification

## Decision

Publish the three exact A2-G3 frozen role-release artifacts to the locked Cloudflare R2 canonical namespace, using immutable payload-first and manifest-last writes. Read every remote object back and verify its exact byte count and SHA-256 before recording WP6 as complete.

This packet authorises publication only. It does not activate any OPT-A selector, consume validation, open the OPT-A-to-OPT-B handoff, or create market, probability, exposure, trading or execution authority.

## Exact upstream authority

- A2-G3 source/build commit: `8c4c6c70da6f3f8b400d06df990500702813ff39`
- A2-G3 workflow run: `30179286521`
- Discovery artifact: `8625089938`
- Development artifact: `8625090401`
- Locked-validation artifact: `8625090861`
- Quarantine disposition: `RETAIN_TRACE_AND_EXCLUDE_FROM_ACCEPTED_OBSERVATIONS`

## Publication identities

| Role | Release ID | Manifest ID |
|---|---|---|
| Discovery | `OPT-A.GBPUSD.DISCOVERY.2021_2023.v2` | `MANIFEST.OPT-A.GBPUSD.DISCOVERY.2021_2023.v2.r1` |
| Development | `OPT-A.GBPUSD.DEVELOPMENT.2024.v2` | `MANIFEST.OPT-A.GBPUSD.DEVELOPMENT.2024.v2.r1` |
| Validation | `OPT-A.GBPUSD.VALIDATION.2025.v2` | `MANIFEST.OPT-A.GBPUSD.VALIDATION.2025.v2.r1` |

## Mandatory sequence

1. Download only the named A2-G3 artifacts from the exact workflow run.
2. Verify every local object against the committed deterministic manifest.
3. Validate the exact manifest-bound operator approval.
4. Confirm the `ovc_r2` remote is configured and every canonical target key is absent.
5. Upload release payloads with immutable writes.
6. Upload each manifest last as the completion marker.
7. Stream every remote manifest and payload object and verify exact bytes.
8. Emit a compact WP6 publication report and retain all selectors at `NONE`.

## Stop conditions

WP6 stops without selector mutation when credentials are unavailable, a target key already exists, local bytes differ, approval binding fails, upload fails, remote verification fails, or the validation lock is not present.

Partial immutable objects are never treated as a completed release without the exact verified manifest. Retry requires a new manifest revision rather than overwrite.
