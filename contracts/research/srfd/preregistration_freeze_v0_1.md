# SRFD WP9 preregistration freeze contract v0.1

Programme: `OVC-SRFD-BENCHMARK-v0.1`  
Packet: `SRFDI-WP9`  
Gate: `SRFDI-G9` (`OPERATOR_ACKNOWLEDGEMENT`)  
Authority before gate: bounded preregistration preparation only.

## Freeze object

The candidate preregistration is:

`registries/research/srfd/SRFD_PREREGISTRATION_CANDIDATE_v0_1.json`

Its byte SHA-256 and canonical logical SHA-256 are bound by
`SRFDI_WP9_PREREGISTRATION_HASH_RECEIPT.json`.

`PREREGISTRATION_FREEZE` at `SRFDI-G9` may make those exact bytes and the
declared decision protocol immutable for the later bounded June run. It does
not authorize the run.

## Frozen-before-June rules

The preregistration fixes the research questions, hypotheses, falsifiers,
population-binding procedure, representation/segmentation/distance/family
candidate sets, parameter ladders, qualifying-configuration rules, stability
metrics and denominators, family-strength evidence rule, invariant-core rule,
ambiguity/residual policies, failure-attribution precedence, T0 capacity
limits, stop conditions, required output tables, and scientific decision
surfaces.

Strong-family evidence is deliberately non-composite. It requires unanimous
support over the declared qualifying-configuration denominator, at least three
distinct qualifying configurations, and at least two distinct enabled
family-method classes. Full assignment is not required; residual and ambiguity
populations remain visible. These rules were chosen before any SRFD June
benchmark result was exposed.

Prohibited after benchmark visibility include selecting the nicest family
count, smallest residual count, most visually pleasing prototype, the method
that best matches an expected narrative, changing threshold/radius, or dropping
a difficult declared method.

## Population binding

WP9 freezes only the procedure. It does not bind the final eligible population
or source release. The historical `8598` C2-state count remains
`NON_BINDING_CAPACITY_AND_COVERAGE_REFERENCE_ONLY`. Exact population/source
identity must be supplied and independently checked at `SRFDI-G-JUNE-AUTH`.

No provider fetch, upstream mutation, June SRFD market-record inspection, or
2025 Validation read is authorized by this packet.

## Run manifest

`SRFD_JUNE_RUN_MANIFEST_TEMPLATE_v0_1.json` is a template only. Every unresolved
population/source/code/artifact field must be bound at the later run-authority
gate. A missing or mismatched preregistration hash, source hash, population
hash, required QA result, or rollback control blocks execution.

## Authority firewall

Until a later explicit `SRFDI-G-JUNE-AUTH = AUTHORIZE_JUNE` decision:

- June benchmark execution is denied.
- 2025 Validation is `LOCKED_UNCONSUMED`.
- representation, normalization, segmentation, distance, family, sensitivity,
  semantic or candidate promotion is denied.
- selector activation/change is denied.
- publication, probability, risk, exposure and execution authority are none.
- PR #371 remains `PRESERVE_DO_NOT_MERGE`.

Rollback: before G9 acknowledgement, replace the candidate only through a new
versioned WP9 candidate and rerun QA. After `PREREGISTRATION_FREEZE`, changes
require a new operator-governed preregistration version; never overwrite the
frozen run identity.
