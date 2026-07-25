# OPT-A v1 Recovery Audit

## Audit identity

- Audit ID: `AUDIT.OPT-A.GBPUSD.2026H1.v1.RECOVERY.WP1`
- Programme: `OVC-OPT-A-V2-IMPLEMENTATION-PLAN-0.2`
- Repository baseline: `a9902c97e21131b1882b4c11ca3a2a79273e7c77`
- Historical release: `OPT-A.GBPUSD.2026H1.v1`
- Decision date: 25 July 2026

## Expected sealed payload

The immutable historical manifest identifies 14 artifacts totalling 13,906,357 bytes. It records one M1 provider file, six monthly H1 provider files, two canonical observation files and five reconciliation/report files.

Hash-locked historical court records:

| Record | Repository path | Git blob SHA-1 | Embedded release hash |
|---|---|---|---|
| Seal manifest | `legacy/quarantine/abcd-engine-v1-c0ad7ba/docs/history/releases/opt-a-discovery-2026-h1/OPT_A_SEAL_MANIFEST.json` | `56367dd59398ff8a64e12cdd48e60178fdb334ce` | `0927f7a2b078d670370eb9ec26718f3e2ff0d97708df1f785a9333264415ef99` |
| Seal record | `legacy/quarantine/abcd-engine-v1-c0ad7ba/docs/history/releases/opt-a-discovery-2026-h1/OPT_A_SEAL_RECORD.md` | `b16aadb0154f86b418b2653e3b33f468952813ae` | references the same seal hash |

## Recovery evidence considered

The pre-R0 evidence-store activation attempted to locate the exact sealed release root at the repository-declared external artifact location and other named candidate locations. The expected 14-file population was not found. Publication stopped before canonical upload.

The historical activation evidence also recorded that the `ovc-evidence` bucket and locked `canonical/` namespace were available, but no authoritative v1 canonical publication occurred.

R0 subsequently preserved the Git court record and classified the operator-local external root, current Windows filesystem and current R2 object inventory as not evaluated by the GitHub runner. WP1 does not reinterpret that limitation as a successful recovery.

## Current evaluation boundary

This WP1 GitHub execution can verify repository bytes and registry state. It cannot inspect `C:\Users\Owner\OVIS\ovc-replay-external-artifacts`, other operator-local disks or environment-only R2 credentials. Therefore:

- historical recovery result: `NO_EXACT_PAYLOAD_MATCH_RECORDED`
- current local re-search: `NOT_EVALUATED_BY_GITHUB_RUNNER`
- current remote re-inventory: `NOT_EVALUATED_BY_GITHUB_RUNNER`
- exact sealed payload availability: `UNAVAILABLE_FOR_REPRODUCTION`

## Decision

The v1 payload recovery path is closed for active programme purposes. `OPT-A.GBPUSD.2026H1.v1` is retained as historical lineage but is unavailable, never published and not reproducible from the exact sealed bytes.

No regenerated or substitute bytes may be published under the v1 release ID, manifest identity, seal ID or canonical namespace. Any new population must use the exact v2 role-aware identities registered by WP1.
