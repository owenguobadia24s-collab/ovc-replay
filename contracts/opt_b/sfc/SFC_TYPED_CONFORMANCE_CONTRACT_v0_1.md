# OVC SFC v0.1 Typed Conformance Contract

Status: inactive conformance capability. Authority: synthetic/fixture/shadow build and QA only.

The normative chain is `C2EStreamEnvelope -> RepresentationPopulation -> RepresentationPack -> RepresentationRecord/Bundle -> ComparabilityDecision -> ComparisonSpec/PairRecord/Surface -> FamilyMethodSpec -> FamilyCatalog/FamilyRecord/Assignment -> FamilyCorrespondence/InvariantCore/MetricRecord -> FamilyEvidenceStream`.

Every derived object carries `first_valid_time` and `evaluation_cutoff` where chronologically meaningful. Its first-valid time is no earlier than every required parent's first-valid time plus any declared confirmation delay. Backdating is forbidden.

Representation namespaces are distinct: `structural_raw`, `structural_derived`, `structural_normalized`, `comparison_only`. Normalization never replaces raw evidence. Family/prototype/distance/outcome/Validation/probability/risk/exposure/execution fields are forbidden from structural representation identity.

Comparability is evaluated before PairID admission and before distance/similarity. A non-comparable pair has no synthetic numeric distance. Each ComparisonSpec declares formula, parameters, precision, equivalence policy, missingness policy, symmetry and only the metric properties it actually claims.

Family evidence is catalog-scoped. Full assignment is not required: MEMBER, RESIDUAL, NOISE, SINGLETON, AMBIGUOUS, NOT_COMPARABLE, NOT_EVALUABLE and QUARANTINED are lawful typed outcomes. Zero supported families and 100% residual are lawful and map to `NO_STABLE_FAMILY`, not a runtime failure. Cross-catalog continuity is evidence, never family identity reuse.

Metric evidence is decomposed. Every rate record stores exact numerator, denominator, rational `numerator/denominator`, or null plus a typed reason when denominator is zero. Hidden composite family-quality scores and post-result threshold selection are forbidden.

The SRFD v0.4 scientific RulePack is an external frozen binding. SFC may wrap it only after proving source hash preservation and shared-input semantic equivalence; SFC does not rewrite its scientific rules.

While SFC is active, `srfd_june_authority_interlock=DENY`. No SFC object grants provider intake, June execution, Validation consumption, production Representation/Normalization/Comparison/Family/Sensitivity selection, selector mutation, publication, semantic promotion, C2P/C2.5/C3 activation, probability, risk, exposure or execution authority.
