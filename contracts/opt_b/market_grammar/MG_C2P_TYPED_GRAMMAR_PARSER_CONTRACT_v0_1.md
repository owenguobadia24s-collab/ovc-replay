# MG C2P Typed Grammar and Parser Contract v0.1

**Contract ID:** `MG-C2P-TYPED-GRAMMAR-PARSER-0.1`  
**Programme:** `OVC-C2E-C2G-C2P-MARKET-GRAMMAR-REMEDIATION-v0.1`  
**Packet:** `MG-WP6`  
**Authority:** inactive, noncanonical, unpublished `SHADOW_EXPERIMENT` only

MG-WP6 implements the frozen MG-D5 typed AST operators exactly: `ALL_OF`, `ANY_OF`, `SEQUENCE`, `WITHIN_N_OBSERVATIONS`, `SAME_OBJECT`, `RELATION_TRANSITION`, `RUN_LENGTH`, and `CONTEXT_AVAILABILITY`.

Every AST node declares `operator`, `input_type`, `output_type`, `domain`, `required_fields`, `children`, and `parameters`. The compiler rejects unknown operators, invalid arity/parameters, child type mismatches, missing required intermediate types, unsupported fields, or an untyped node.

A grammar fixture is an immutable local candidate object only. It carries a deterministic SHA-256 over its canonical payload, `canonical=false`, `published=false`, and `authority_state=SHADOW_EXPERIMENT`. Creating the fixture is not publication, activation or grammar promotion.

Layer slots are typed and explicit: `context`, `location`, `condition`, `episode_phase`, `event`, `response`, `transition`, and `possible_resolution`. A slot may be `null`; absence is never inferred.

Parser results are exactly `NO_MATCH`, `PARTIAL_MATCH`, `AMBIGUOUS_MATCH`, `GRAMMAR_MATCH`, `GRAMMAR_CONTRADICTION`, or `GRAMMAR_INVALIDATED`. `GRAMMAR_CONTRADICTION` requires an exclusivity-registry proof or explicit conflicting evidence bound to such a proof; ordinary structural variation cannot create contradiction. `GRAMMAR_INVALIDATED` requires an explicit invalidating condition present in the frozen grammar fixture.

Every parse result retains the grammar release identity/hash, nearest family and variant, medoid distances, current/completed phases, lawful next phases, missing evidence, conflicting evidence, invalidation reasons and complete upstream lineage.

Construction and parsing may not consume future paths, outcomes, probability, risk, exposure, execution, trade labels or operator semantic promotion. No parser output grants market meaning or candidate authority.

Acceptance requires deterministic grammar hashing, compilation of all eight frozen operators, invalid operator/type fixtures, parser status coverage, complete lineage/evidence retention, input-order/path/machine independence, focused and complete repository tests, FINAL_HEAD, compatibility, merge readiness and zero unresolved review threads.

Rollback removes or supersedes the inactive compiler/parser and preserves the immutable fixture bytes, tests, QA, decision and all upstream C2/C2E/C2G records. It never mutates a grammar fixture in place.
