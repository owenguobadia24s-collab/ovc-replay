# OPT-A to OPT-B Handoff Contract v0.2

## Purpose and authority

This contract defines the only lawful v2 boundary from a sealed OPT-A role release into OPT-B.C1. It does not create a release, activate a selector or authorise OPT-B semantics. WP3 remains contract-only.

Contract ID: `OPT-A-TO-OPT-B-HANDOFF-0.2`

## One-way dependency

```text
provider objects -> OPT-A role release -> sealed handoff -> OPT-B.C1 -> OPT-B.C2
```

OPT-B may not:

- scan arbitrary external directories;
- read mutable OPT-A workspaces;
- import quarantined v1 release payloads;
- infer source identity from filenames alone;
- substitute H1 provider-native objects for missing M1 lineage;
- consume validation by default;
- write corrections back into OPT-A release bytes or lineage.

## Required handoff identity

A handoff record binds exactly one role release and contains:

- `handoff_id` and contract version;
- exact `release_id`, `manifest_id` and research role;
- instrument and UTC half-open role interval;
- source/build repository commit;
- release-manifest SHA-256;
- frozen workspace-inventory SHA-256;
- remote-verification receipt ID when remote verified;
- provider-intake, source-object, clock and aggregation contract IDs;
- accepted observation surfaces and their schema IDs;
- source-object inventory counts by timeframe and side;
- accepted, rejected and quarantined counts by surface;
- gap and reconciliation summaries;
- QA state, lifecycle state, authority state and selector state;
- explicit downstream permissions and prohibitions;
- validation-consumption state and approval ID when applicable.

The handoff record contains compact governance metadata only. It does not embed raw or canonical market tables.

## Accepted observation surfaces

The standard handoff may advertise these independently versioned surfaces:

```text
M1_PROVIDER_NATIVE_BID
M1_PROVIDER_NATIVE_ASK
M15_M1_DERIVED_BID
M15_M1_DERIVED_ASK
H1_M1_DERIVED_BID
H1_M1_DERIVED_ASK
H1_PROVIDER_NATIVE_BID
H1_PROVIDER_NATIVE_ASK
H2_M1_CHAIN_DERIVED_BID
H2_M1_CHAIN_DERIVED_ASK
H4_M1_CHAIN_DERIVED_BID        optional
H4_M1_CHAIN_DERIVED_ASK        optional
D1_M1_CHAIN_DERIVED_BID        optional
D1_M1_CHAIN_DERIVED_ASK        optional
BID_ASK_PAIR_QUALITY
H1_RECONCILIATION
GAP_AND_QUARANTINE_LEDGER
```

OPT-B.C1 may consume only surfaces explicitly listed as `HANDOFF_ELIGIBLE` in the sealed record.

## Handoff states

```text
DRAFT
LOCAL_VERIFIED
REMOTE_VERIFIED
HANDOFF_ELIGIBLE
SHADOW
ACTIVE
BLOCKED
SUPERSEDED
```

State changes are monotonic except for an explicit rollback from `SHADOW` or `ACTIVE` to selector `NONE`. Historical records are never rewritten.

- `DRAFT`: schema-valid proposal only.
- `LOCAL_VERIFIED`: release bytes and manifest verified locally.
- `REMOTE_VERIFIED`: exact remote bytes and manifest verified.
- `HANDOFF_ELIGIBLE`: all required QA and governance gates passed.
- `SHADOW`: downstream compatibility replay permitted, but no active replacement authority.
- `ACTIVE`: role selector points to this exact release/manifest pair after operator approval.
- `BLOCKED`: handoff cannot progress until a new reviewed record resolves blockers.
- `SUPERSEDED`: historical lineage only; not a selector or rollback target.

WP3 fixtures and records remain `DRAFT` with selector `NONE`.

## Selector binding

A role selector binds all of the following atomically:

```text
role
release_id
manifest_id
handoff_id
remote_verification_receipt_id
source_commit
activation_decision_id
```

A path, latest-file convention, bucket prefix or release ID alone is insufficient.

The three v2 role selectors are independent but must be updated as one reviewed selector-set operation:

- discovery -> `OPT-A.GBPUSD.DISCOVERY.2021_2023.v2`
- development -> `OPT-A.GBPUSD.DEVELOPMENT.2024.v2`
- validation -> `OPT-A.GBPUSD.VALIDATION.2025.v2`

Until later approval, every selector remains `NONE`. Rollback sets the v2 selector set to `NONE`; historical v1 reactivation is prohibited.

## Validation boundary

The validation release is registered as `LOCKED_UNCONSUMED`.

A validation handoff requires:

- exact validation release and manifest IDs;
- a valid `validation_access_approval_id`;
- approved purpose and bounded consumer;
- an access receipt recording first and subsequent reads;
- proof that discovery/development contracts and thresholds were frozen before access.

Without those fields, validation surfaces are not handoff eligible and the default command path must deny access.

## Handoff QA requirements

A handoff is blocked when any of these is true:

- manifest or inventory mismatch;
- missing source-object identity;
- unresolved schema fingerprint mismatch;
- accepted bucket with incomplete parent timestamps;
- cross-side or cross-role contamination;
- missing gap or quarantine summary;
- unresolved release-ID reuse;
- selector state inconsistent with lifecycle or authority state;
- validation access absent or invalid;
- source/build commit not present in Git;
- remote verification claimed without a receipt.

## Compatibility boundary

Later shadow compatibility replay may compare v1 and v2 over a shared interval, but it may not retroactively relabel v1 outcomes or seed v2 parameters from historical candidates. Differences must use explicit reason codes and remain linked to their release identities.

## WP3 consequence

WP3 freezes the handoff schema and selector rules only. No handoff is eligible, shadowed or active; no OPT-B replay is authorised.