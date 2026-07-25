# OPT-A v2 contracts

The active OPT-A contract set now includes release governance plus the WP3 provider, source-object, clock, aggregation, gap, volume, reconciliation and OPT-A-to-OPT-B handoff boundaries.

- `OPT_A_RELEASE_LIFECYCLE_CONTRACT_v0_2.md` — release identity, disposition and selector eligibility.
- `OVC_EXTERNAL_ARTIFACT_ROOT_CONTRACT_v0_1.md` — local storage boundary.
- `OPT_A_PROVIDER_INTAKE_AND_SOURCE_OBJECT_CONTRACT_v0_2.md` — Dukascopy monthly M1/H1 BID/ASK intake and immutable source-object identity.
- `OPT_A_CLOCK_AGGREGATION_GAP_VOLUME_RECONCILIATION_CONTRACT_v0_2.md` — UTC half-open clocks, A-L 2H spine, exact parent sets, no-fill, volume and H1 reconciliation.
- `OPT_A_TO_OPT_B_HANDOFF_CONTRACT_v0_2.md` — sealed one-way release handoff into OPT-B.C1.

WP3 contracts and fixtures are implementation authority only. They do not download provider bytes, create a release, publish to R2, activate a selector or authorise OPT-B research.
