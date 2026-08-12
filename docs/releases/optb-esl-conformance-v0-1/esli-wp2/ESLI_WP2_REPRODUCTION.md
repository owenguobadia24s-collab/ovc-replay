# ESLI-WP2 reproduction

Targeted: `python -m pytest -q tests/opt_b/esl/test_esli_wp2_canonical_serialization.py`

Dependent: `python -m pytest -q tests/opt_b/esl`

Repository: `python -m pytest -q`

WP2 is deterministic and standard-library only. Production/reference canonicalizers are independent modules. Rollback is removal or forward supersession of WP2 serializer/profile/golden-corpus surfaces; WP1 identities and all upstream records remain untouched.
