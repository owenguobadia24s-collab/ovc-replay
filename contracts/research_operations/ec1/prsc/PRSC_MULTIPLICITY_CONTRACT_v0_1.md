# PRSC Multiplicity Contract v0.1

## Scope
This contract governs PRSCI-WP5 multiplicity accounting and familywise adjustment. It creates no scientific promotion, candidate freeze, owner-layer, Validation, publication, probability, risk, exposure or execution authority.

## Family constitution
- Every confirmatory hypothesis belongs to one exact `ScientificHypothesisFamilyRegistry` generation.
- Parent/child identities are explicit; family membership may not shrink after results are observed.
- Exact semantically identical hypotheses may collapse for inference only when provenance for every original hypothesis is retained.
- Similar, near-duplicate or inconvenient hypotheses may not be collapsed by convenience.

## Specification opportunity accounting
- Declared, attempted, failed and post-hoc configurations remain visible in `SpecificationOpportunityLedger`.
- Failed or not-evaluable configurations are evidence and cannot be silently removed from the search surface.

## Shared reference draws
- Familywise adjustment uses shared reference draws across the whole registered family so cross-hypothesis dependence is retained.
- Missing hypotheses, unequal draw counts or per-hypothesis independent redraws fail closed.

## Multiplicity method
- Base v0.1 reference method is deterministic step-down max-statistic familywise adjustment under a versioned `MultiplicityMethodPack`.
- Any alpha is pack-scoped scientific configuration; no universal alpha is embedded in PRSC runtime.
- Adjusted p-values are monotone in the ordered step-down sequence and preserve exact family provenance.

## Review-capacity firewall
- Review capacity cannot create hidden top-N scientific selection.
- If the whole registered family cannot be reviewed in one batch, deterministic batching or family-level defer is required.
- A partial strongest-only review is `REVIEW_CAPACITY_EXCEEDED`, not a valid scientific subset.

## Fail-closed conditions
Family shrink after results, incomplete shared draws, semantic-collapse without exact identity, lost provenance, hidden top-N review, post-hoc deletion, or unregistered method packs are blocking.

## Preserved constraints
F0-A remains `HOLD`; Validation remains `LOCKED_UNCONSUMED`; CandidateFreeze remains `NONE`; and real-source PRSC remains denied until `PRSCI-G-EC1-CHALLENGE`.
