# SRFDI-WP2C Source Adapter and June Authority Binding Contract v0.1

## Status and authority

This contract is a bounded corrective implementation surface under `OVC-SRFD-IMPLEMENTATION-PLAN-0.1` after `SRFDI-G9 PREREGISTRATION_FREEZE`. It grants no June benchmark execution authority and no scientific, selector, publication, Validation, probability, risk, exposure or execution authority.

`SRFDI-WP2C` corrects engineering omissions discovered during `SRFDI-G-JUNE-AUTH` preflight. It may not alter the frozen G9 preregistration, choose representation semantics that G9 did not freeze, or reinterpret an upstream C2 record to obtain a desired benchmark population.

## 1. Read-only C2/C1 source binding

The source adapter MUST:

1. bind an already-lawful upstream replay release, source commit, source slice, source-manifest SHA-256, output-manifest SHA-256 and active C2 model release;
2. perform no provider fetch and no upstream write;
3. validate C2 target membership independently through the exact parent C1 record and its observation `open_time`, rather than trusting a C2 `target_eligible` flag in isolation;
4. preserve exact C2 five-axis payloads (`LOCATION`, `MOTION`, `ORGANISATION`, `INTERACTION`, `QUALITY`) including status, value, reason and measurement;
5. preserve level/container/relation identities, persistence, continuity, parameter-pack identity and source lineage without converting them into selected representation coordinates;
6. reject future/outcome/family/grammar/probability/risk/exposure/execution fields;
7. leave upstream bytes untouched.

Target records with lawful explicit `NOT_EVALUATED`, `NOT_EVALUABLE`, `CENSORED`, `CONFLICT` or `QUARANTINED` axis state remain visible in the source population. They are not globally removed merely because one representation may be unable to consume them. Representation-specific computability remains a later configuration-level decision under the already frozen missingness doctrine.

A malformed target C2 record that lacks a required five-axis structural field may enter the explicit population exclusion ledger with `REP_REQUIRED_DIMENSION_MISSING`. A source-binding, parent-lineage, chronology, target-classification or authority mismatch is a blocking source error, not a tunable exclusion.

## 2. Schema-preserving adapter boundary

The adapter output is deliberately **not** a `RepresentationPack`. It exposes `native_c2` and `source_lineage` namespaces plus comparability metadata. It MUST NOT silently create aliases such as `location = measurement`, `motion = category`, normalized coordinates, selected relation features, episode summaries, or any other scientific feature choice.

The implementation registry currently maps SRFD implementation classes to architecture candidates, but the repository does not materialise exact real-source `RepresentationPack.required_fields` and transform semantics for the G9-frozen candidate IDs. Choosing those mappings after the preregistration freeze would be a scientific-contract change. `SRFDI-WP2C` therefore records this as an unresolved downstream authority blocker rather than inventing the mappings.

The neutral C2E ledger-input adapter may reuse the existing inactive deterministic shadow ledger contract only to expose a read-only input surface. It does not activate C2E, select episode semantics or promote that shadow ledger into canonical authority.

## 3. Population binding

The population binder MUST produce, before any benchmark run:

- exact source-binding hash;
- exact source-record count;
- lexicographically sorted eligible target record IDs;
- SHA-256 of the canonical eligible-ID list;
- context-only count/hash;
- explicit target exclusion ledger and hash;
- computability counts inside the eligible population;
- deterministic population ID.

The historical `8,598` reference becomes authoritative only if the frozen procedure independently reproduces both the count and exact record-ID hash from lawful source records. No family, distance, stability, recurrence or downstream benchmark result may affect population membership.

## 4. Fail-closed June run authority binding

The existing fixture-only `authority_guard("june_market_benchmark")` remains unchanged and denied.

A separate bounded-run verifier may emit a `JuneRunAuthorityToken` only when all of the following are exact:

- operator decision gate is `SRFDI-G-JUNE-AUTH`;
- operator decision is `AUTHORIZE_JUNE`;
- decision authority delta is bounded June execution only and preserves every other firewall;
- G9 preregistration byte and logical hashes match the frozen values;
- source release/commit/hashes are fully bound;
- population ID/count/eligible-ID hash/exclusion hash are fully bound;
- implementation commit and dependency-manifest hash are fully bound;
- manifest candidate sets/capacity/QA/rollback content remains within the frozen run manifest;
- provider fetch and upstream mutation remain forbidden;
- Validation remains `LOCKED_UNCONSUMED`;
- selector, scientific promotion, publication, probability, risk, exposure and execution remain `NONE`;
- the operator decision binds the exact pre-authority manifest hash and the materialised manifest binds the exact operator-decision hash.

No token exists before an actual operator `AUTHORIZE_JUNE` decision. Synthetic positive tests of the verifier are contract tests only and grant no authority.

## 5. Corrective packet acceptance

`SRFDI-WP2C` engineering PASS requires:

- schema-preserving C1/C2 source adapter tests PASS;
- independent target-window reproduction tests PASS;
- missingness retention and explicit malformed-record exclusion tests PASS;
- source/tamper/outcome/authority negative tests PASS;
- deterministic order-independent population identity PASS;
- neutral C2E input adapter determinism PASS;
- bounded-run authority verifier positive/negative contract tests PASS;
- default June denial remains PASS;
- repository-wide exact-head tests PASS;
- no provider fetch, June benchmark execution, Validation access, selector change, promotion or publication occurs.

Engineering PASS does **not** mean `SRFDI-G-JUNE-AUTH` is gate-ready. If exact real-source representation-pack field/transform semantics remain absent, the programme MUST stop with `FROZEN_REPRESENTATION_PACK_FIELD_MAPPING_NOT_MATERIALISED`. The smallest lawful next action is an operator-governed preregistration supersession/version unless an already-frozen authoritative mapping is found.

## 6. Rollback

Rollback is additive and non-destructive: revert this bounded packet with a later commit or leave the adapter unused. Do not mutate accepted upstream replay evidence, rewrite the G9 preregistration, force-push, merge PR #371, fetch a provider, consume Validation or execute June.
