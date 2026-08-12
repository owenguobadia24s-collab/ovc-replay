# ESLI-WP3 reproduction

Targeted: `python -m pytest -q tests/opt_b/esl/test_esli_wp3_occurrence_compiler.py`

Dependent: `python -m pytest -q tests/opt_b/esl`

Repository: `python -m pytest -q`

Reference performance: load `fixtures/opt_b/esl/wp3/bootstrap_c2_input.json` and call `measure_reference_compiler(..., repetitions>=20)`. The QA packet records the measured p50/p95 and exact environment; G4, not WP3, is the first authority to freeze `BootstrapPerformanceBudget.v1`.

Rollback removes/forward-supersedes WP3 adapter/compiler/pack/fixture only; no C2/C2E/C2P identity or selector is changed.
