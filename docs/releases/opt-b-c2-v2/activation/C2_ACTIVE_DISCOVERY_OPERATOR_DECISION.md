# C2 ACTIVE_DISCOVERY selector and legacy retirement

## Decision

**PASS — activate the exact remote-verified C2 Discovery release and retire B-STATE-0.3b atomically.**

The transaction activates only `OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v1` through selector set `SELECTOR.OPT-B.C2.GBPUSD.v1`. The remotely verified Development release remains an unselected reference release.

## Exact active identity

- Release: `OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v1`
- Manifest: `MANIFEST.C2.OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v1.r1`
- Manifest SHA-256: `c5723e9e6837816c9ff0ed023112890aee6589e22518fe8365cbff2653169a33`
- R2 verification workflow: `30214691361`
- R2 verification result: `PASS_FULL_REMOTE_BYTE_VERIFICATION`

## Atomic retirement

`B-STATE-0.3b` becomes `HISTORICAL_SUPERSEDED`. Runtime imports, parentage, selector eligibility, parameter-source eligibility and rollback eligibility remain denied.

## Rollback

Rollback sets every C2 selector to `NONE` and returns operation to the existing C1-only boundary. It must never reactivate B-STATE-0.3b.

## Retained authority

- C1 remains `SHADOW`.
- C2 Development selector remains `NONE`.
- Validation remains `LOCKED_UNCONSUMED`.
- C2E, C2.5 and C3 remain deferred.
- Probability, exposure, trading and execution remain `NONE`.

This decision changes research-selection authority only. It grants no trading or execution authority.
