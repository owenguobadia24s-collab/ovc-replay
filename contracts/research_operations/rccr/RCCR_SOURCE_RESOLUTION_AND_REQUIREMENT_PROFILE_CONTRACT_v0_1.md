# RCCR Source Resolution and Requirement Profile Contract v0.1

Status: IMPLEMENTED INACTIVE / NON-AUTHORITATIVE RCCR SYNTHESIS ONLY.

## Constitutional boundary

RCCR source resolution is read-only. An exact source identity, source owner, semantic generation, semantic payload hash, first-valid time, authority state and provenance references are required before a source may enter RCCR synthesis. A title, display label, path, nearby file or semantic similarity is never sufficient identity. Protected Validation content is denied before payload resolution. External evidence may motivate or crosswalk requirements but has `authority_effect=NONE` and cannot create OVC owner authority.

## SourceResolutionManifest

The manifest binds the sorted exact source set and preserves each owner's state. It is deterministic across request order. It records that protected payloads were not opened and has no authority effect.

## Requirement derivation

Implementation derivation modes are `SOURCE_EXPLICIT`, `SOURCE_CROSSWALK`, `PROTOCOL_DERIVED`, `THEORY_IMPLICATION_DERIVED`, `OPERATOR_FORMALISED`, and `EXTERNAL_FINDING_CROSSWALK`. They project into the already-frozen canonical `ResearchRequirementProfile.derivation_class` vocabulary without changing that schema. Any unresolved semantic choice, operator formalisation, or non-explicit theory implication/falsifier requires a governed human-review source. External-finding crosswalks always require review and remain non-authoritative.

Requirement arrays and derivation references are canonicalised deterministically. The exact source identity remains identity-bearing, so two different source objects with identical wording do not collapse into one requirement profile.

## Currentness

Source-token change yields `STALE_SOURCE`; protocol-token change yields `STALE_PROTOCOL`; otherwise the exact dependency remains `CURRENT`. Later source or capability change never rewrites historical RCCR records.

## Denials

The implementation fails closed for missing exact source identity, duplicate source identity, missing owner/authority state, protected Validation, incomplete source metadata, unknown derivation mode, required-but-missing human review, and dependency-index collision.

Authority effect: NONE. No real-source EC1 execution, Path-2 execution/preregistration, capability activation, Validation consumption, publication, probability, risk, exposure, trading, execution, or agent-write authority is created by this contract.
