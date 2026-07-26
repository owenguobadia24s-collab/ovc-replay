# OPT-B.C1 v2 B1-G1 Operator Decision

## Decision

`PASS — EXACT WP4 CANDIDATE INVENTORY ACCEPTED; DURABLE LOCAL FREEZE AUTHORISED`

## Review basis

The review is bound to WP4 workflow run `30185680001`, execution commit `2e2d84ad34fae02992a7861d194c12e0bdbd0c1f`, candidate artifact `8626942276` and archive SHA-256 `fb52ea4f84fa7c1d79c9c524470d6722ab82b09a5ed4d4f0278fda4d330eabfc`.

The embedded `WP4_INVENTORY.json` is bound by SHA-256 `39f55e923fa0a8302024f02d862d294ad9d8448fe197a9849ee9ec0f15d4a383`. Independent full-byte verification confirmed every one of its 192 payload entries, all 36,169,581 payload bytes and all 212,764 unique `c1:<sha256>` record identities.

## Exact accepted inventory

| Role | Files | Bytes | Records |
|---|---:|---:|---:|
| Discovery 2021–2023 | 144 | 27,450,668 | 159,892 |
| Development 2024 | 48 | 8,718,913 | 52,872 |
| **Total** | **192** | **36,169,581** | **212,764** |

The role/clock/side cardinalities match the WP4 execution receipt. There are zero duplicate record IDs and zero missing or hash-mismatched payload files.

## Parent and QA findings

- Discovery is bound to `OPT-A.GBPUSD.DISCOVERY.2021_2023.v2` and manifest SHA-256 `0cbcafa9421449574b61bfeec24f634de99cbbbc6e7a53d09ace8f702182ab8c`.
- Development is bound to `OPT-A.GBPUSD.DEVELOPMENT.2024.v2` and manifest SHA-256 `25e1be8a7edb0e96017c45bf35f4e788345f94b22a8ed9bb0874c86338ba64cc`.
- The deterministic second replay matched the complete first inventory.
- The 12,104 Discovery and 4,862 Development upstream quarantine records remain excluded.
- No interpolation, gap repair, cross-side substitution, legacy input or Validation payload was used.
- Validation remains `LOCKED_UNCONSUMED`.

## Authority delta

B1-G1 authorises exactly one controlled local mutation: `c1 freeze-release` may promote the accepted candidate into immutable external release roots for:

- `OPT-B.C1.GBPUSD.DISCOVERY.2021_2023.v1`
- `OPT-B.C1.GBPUSD.DEVELOPMENT.2024.v1`

The freeze must use candidate artifact `8626942276` and the exact accepted inventory hash. It must refuse overwrite, identity drift, missing payloads, changed bytes or a different parent release.

This decision does **not** claim that either release is already `RELEASE_FROZEN` or `LOCAL_VERIFIED`. Those states require the subsequent freeze execution, immutable local manifests and a complete post-freeze byte verification receipt.

## Authority retained

- C1 selectors remain `NONE`.
- R2 publication remains denied pending a separate WP5 approval.
- C2 consumption remains denied pending a separate handoff review.
- Probability, exposure, trading and execution authority remain `NONE`.

## Rollback

Any failed freeze attempt is discarded in full. The system returns to the WP4 QA-passed local-candidate state, leaves OPT-A selectors unchanged, keeps all C1 selectors at `NONE` and never reactivates historical OPT-A v1 or legacy OPT-B.

## Next work packet

`OPT-B.C1 v2 WP4F — durable local release freeze and full-byte verification`
