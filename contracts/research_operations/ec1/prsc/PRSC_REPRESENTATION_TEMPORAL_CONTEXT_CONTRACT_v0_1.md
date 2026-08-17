# PRSC Representation, Temporal and Context Contract v0.1

Authority effect: **NONE**. This contract implements PRSCI-WP3 challenge machinery only. It does not select a representation, grant SRI/FDI scientific or production authority, change EC1 candidate identity, mutate OccurrenceContext, open Development/Validation, or create CandidateFreeze/semantic/exposure authority.

Conformance rules:
1. the frozen EC1 base representation remains immutable; challenger representations are evidence views, never winners or replacement candidates;
2. every declared representation challenger is accounted as evaluable, not-comparable, not-evaluable or failed; no hidden top-N, post-hoc winner or denominator shrink is permitted;
3. same-source population crosswalks are directional correspondence evidence, not identity, and split/merge/ambiguous/unmatched states remain explicit;
4. candidate invariant cores may be claimed universal only when every declared representation is evaluable; otherwise the result is a typed partial core and shell;
5. temporal challenges use predeclared year/fixed blocks, preserve all denominators and separate support distribution from evaluability drift;
6. leave-one-block-out and within-Discovery forward-support diagnostics do not become replication evidence;
7. OccurrenceContext remains `STRATIFIER_ONLY` and has `structural_identity_effect=NONE` in base PRSC;
8. the time-by-context matrix is complete over the declared Cartesian product, including empty/not-evaluable cells; no post-hoc applicability mutation is permitted;
9. no latent regime, causal, probability, risk, exposure or execution meaning is inferred from temporal/context heterogeneity.

Rollback is forward-only: quarantine or supersede a non-conformant WP3 challenge implementation while preserving the frozen EC1 base representation, owner records and prior PRSC evidence.