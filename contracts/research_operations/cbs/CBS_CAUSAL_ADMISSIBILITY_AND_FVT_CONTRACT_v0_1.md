# CBS Causal Admissibility and FVT Contract v0.1

`BoundarySupportVector` and `CausalBoundaryAdmissibilityVector` are distinct. Structural location stability never grants causal or first-valid status.

Every estimate preserves `candidate_onset_time`, `effective_time`, `confirmation_time`, `first_valid_time` and `evaluation_cutoff`. Causal admission requires an explicitly registered online-causal or confirmation-delayed route and `first_valid_time <= evaluation_cutoff`; knowledge cannot be backdated. B3 and all retrospective methods are comparison-only, always have `causal_admissibility=false`, and may not join C2E lifecycle or owner activation paths.

Late confirmation, source gaps, release censor, warmup and method abstention remain typed. `CENSOR_RELEASE_END` is not termination. Retrospective agreement without a lawful causal route yields `CAUSAL_ADMISSION_FAIL` while preserving structural support evidence.
