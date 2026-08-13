# OPT-B ESL Structural Organisation Interface Compatibility Contract v0.1

Programme: `OVC-OPTB-ESL-CONFORMANCE-v0.1`  
Packet/Gate: `ESLI-WP6 / ESLI-G6`  
Plan: `OVC-OPTB-ESL-CONFORMANCE-IMPLEMENTATION-PLAN-0.1-REVISED-2`  
Authority: `INACTIVE_CONFORMANCE_ONLY`; authority delta `NONE`.

## Purpose

This contract materialises the generic Structural Organisation Interface (SOI) without selecting an organisation topology, discovery method, scientific threshold, family catalogue, or semantic vocabulary.

`frozen StructuralOccurrence population -> declared representation/comparison surface -> SOI topology view`

SOI asks what forms of organisation may be represented over a frozen population. A topology is the form of organisation being tested; a method is the exact procedure that produced one view. They are separate identities.

## Topology constitution

The registry contains exactly:

- `FAMILY`: discrete recurring groups; compatibility surface for existing FDI/C2G evidence.
- `HIERARCHY`: nested or multi-resolution organisation.
- `OVERLAP`: non-exclusive multi-membership organisation.
- `GRAPH`: relational/network organisation without required community partition.
- `CONTINUUM`: continuous or neighbourhood variation without forced categories.
- `COMPOSITION`: reusable structural components and combinations.

Every topology has one maturity:

- `INTERFACE_ONLY`: the contract exists but no executable adapter is materialised. Invocation MUST fail closed with `SOI_ADAPTER_NOT_MATERIALIZED:<topology>`.
- `EXECUTABLE_INACTIVE`: an exact compatibility adapter exists, but it carries no active topology, method, scientific, family, semantic, publication, Validation, probability, risk, exposure, or execution authority.

WP6 permits only `FAMILY=EXECUTABLE_INACTIVE`, because the completed and preserved SFC/FDI programme already owns a typed `FamilyCatalog` result surface. The other five topologies remain `INTERFACE_ONLY`. WP6 adds no hierarchy, overlap, graph, continuum, composition, clustering, assignment, thresholding, or benchmark algorithm.

## FAMILY compatibility adapter

`SFC.FamilyCatalog.v0.1 -> ESLI.SOI.FAMILY.FDI_COMPAT.v0.1 -> SOIViewResult`

The adapter SHALL:

1. bind the exact preserved `OVC-SFC-v0.1` source result ID, logical hash, population, representation pack, comparison specification, method/configuration, FVT, and evaluation cutoff;
2. validate the source catalog and all family/assignment logical hashes under the source SFC serializer;
3. preserve family records, assignments, residuals, noise, singletons, ambiguity, not-comparable, not-evaluable and quarantine states;
4. preserve `NO_STABLE_FAMILY` as a null scoped only to `FAMILY`; it MUST NOT infer `NO_STABLE_ORGANISATION`;
5. expose a raw `SOIViewResult`, not an `OrganisationEvidenceSet`, support decision, canonical family catalogue, or semantic term;
6. keep topology and source method identities explicit and separate;
7. reject outcome, Validation, forecast, probability, risk, exposure, execution, causal/mechanism, semantic-admission, production-selector and canonical-family fields recursively;
8. leave the exact source catalog immutable and independently addressable.

The adapter SHALL NOT call a discovery algorithm or recompute the source catalog. Existing `src/ovc/opt_b/sfc/fdi.py` machinery remains SFC-owned and preserved.

## WP7 ownership boundary

WP6 does not decide whether a topology is supported. `OrganisationViewResult`, denominator metrics, correspondence, disagreement, invariant evidence, `OrganisationEvidenceSet` and any `OrganisationDecisionRulePack` belong to ESLI-WP7. A raw FAMILY catalog is evidence for one exact discrete hypothesis only.

## Authority boundary

Every output records:

- `topology_activation=NONE`
- `family_promotion=NONE`
- `method_selection=NONE`
- `scientific_support_disposition=NONE`
- `semantic_promotion=NONE`
- `validation_consumption=LOCKED_UNCONSUMED`
- `publication=NONE`
- `probability_risk_exposure_execution=NONE`

Determinism, schema validity, recurrence, family count, assignment coverage, low residual rate, or an attractive catalog never changes those values.

## Failure and rollback

Unknown topology, incomplete registry, invalid source hash/schema, non-inactive source authority, undeclared adapter, or reserved-field leakage fails closed. A failed optional SOI enrichment never invalidates a lawful base StructuralOccurrence.

Rollback is forward-only: supersede/remove the WP6 SOI contract, schema, registry, FAMILY adapter and fixtures while preserving ESLI-WP0–WP5 and all SFC/FDI/SRFD historical records and identities. No selector change, data migration, force-push, history rewrite, provider action, Validation read, or publication is required.
