# OVC Shared Systems DSAI shadow-consumer contract v0.1

Status: `SHADOW_ONLY` under `SHSI-WP7`; authority effect `NONE`.

The DSAI consumer remains `OVC-DSAI-v0.1` at its exact current state. Its current
execution, security, qualification, receipt and currentness records remain controlling.
This contract adds a zero-write Shared Systems consumption manifest and frozen shadow
context only; it does not change the DSAI current binding or any ORCH, merge, security,
TRUSTED, Validation, scientific, publication, probability, risk, exposure or execution
authority.

Environment, run, assurance, receipt and currentness surfaces use one generic
identity-preserving wrapper. The wrapper maps the complete source object to
`source_record`, records a separate wrapper identity and proves exact unwrap. It may
not rename fields, coerce meanings, invent semantics or treat wrapper identity as the
source identity.

Shadow comparison operates on exact frozen common records. Every declared mandatory
semantic path must agree with the current DSAI record. An expected divergence cannot
cover a mandatory path; any mandatory divergence blocks. DSAI security refusals must
remain refusals under the Shared Systems six-factor decision and neither path may
reveal protected metadata.

Adapter complexity is evaluated against the frozen WP6 budget. All five surfaces must
be covered; adapters remain inactive, per-adapter mapping count stays one, generic code
surface and wrapper byte overhead remain within their exact caps, and incident
contribution remains zero. A budget miss blocks rather than relaxing the budget.

Rollback: remove the shadow manifest, context, wrappers and comparison evidence. The
existing DSAI current path remains unchanged and controlling throughout.
