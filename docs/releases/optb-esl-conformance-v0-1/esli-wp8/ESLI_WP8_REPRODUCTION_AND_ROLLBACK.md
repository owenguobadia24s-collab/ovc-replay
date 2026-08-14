# ESLI-WP8 reproduction and rollback

Targeted assurance: `pytest -q tests/opt_b/esl/test_esli_wp8_cei.py tests/opt_b/esl/test_esli_wp7_organisation_evidence.py`.

Repository assurance is provided by the canonical `tests` workflow plus runner parity, pytest/unittest parity, FINAL_HEAD profile, SIQ READY and exact-final merge readiness.

Rollback: forward-supersede WP8-only CEI artifacts and package exports while preserving WP0-WP7 evidence, identities and Git history. No force-push or historical rewrite.
