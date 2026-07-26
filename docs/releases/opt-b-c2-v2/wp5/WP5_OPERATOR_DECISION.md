# OPT-B.C2 v2 WP5 — Canonical Shard Reconciliation

**Decision: BLOCKED — canonical C1 intake is reconciled, but the published C1 record shape does not satisfy the current C2 market engine contract.**

## Accepted reconciliation

The WP5 runner now consumes the actual immutable release layout:

- 192 compressed monthly C1 record shards;
- two manifest-bound release descriptors;
- two completion manifests;
- 194 manifest-bound payload objects and 196 total canonical objects including manifests.

The earlier count of 194 is retained with corrected meaning: it is the number of manifest-declared payload objects. It excludes the two completion manifests. No canonical object is missing.

Before reading a record, the runner binds the exact release and manifest identities, verifies the manifest SHA-256, verifies every declared payload size and SHA-256, rejects undeclared or path-unsafe files, and checks the exact shard inventory for each role, clock and price side.

Persistence and transitions are isolated by role, clock, side and evaluation scope. Shard or directory order cannot create a transition across scopes.

## Blocking contract mismatch

The published shards contain the real `ovc-c1-bar-primitives/v0.1` records produced by C1 WP4: 18 primitive measurements, `clock`, `price_side`, `timestamp_ms`, source lineage and exact OPT-A parent identity.

The current C2 fixture engine was tested against a synthetic envelope that additionally contains absolute `open`, `high`, `low`, `close`, range and swing boundaries, `prior_range`, canonical close/first-valid timestamps and combined-scope context. Those fields are not present in the immutable C1 release bytes.

The runner therefore fails closed with `BLOCKED_C1_C2_RECORD_CONTRACT_MISMATCH`. It will not derive, invent, default or silently reconstruct missing price, level, container, chronology or cross-clock inputs.

## Safe operator command

The downloaded releases may be fully verified without attempting replay:

```powershell
$env:PYTHONPATH = "src"
python scripts/opt_b/run_c2_wp5_replay.py `
  --release-root $C1Root `
  --output-root $C2Output `
  --verify-only
```

Expected verification status:

```text
PASS_CANONICAL_MANIFEST_AND_FULL_BYTE_VERIFICATION
```

This verification creates no C2 candidate authority.

## Authority retained

- Actual Discovery and Development replay: `NOT_EXECUTED`.
- Local C2 candidate release: `NONE`.
- Publication, selector and activation: `NONE`.
- Validation: `LOCKED_UNCONSUMED`.
- Probability, exposure, trading and execution: `NONE`.

The next required work is a bounded C2 market-input contract and engine realignment using the published C1 primitive schema and exact OPT-A price parents, followed by renewed synthetic trust before C2-G4 replay.
