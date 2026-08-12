# ESLI-WP1 reproduction

Targeted:
`python -m pytest -q tests/opt_b/esl/test_esli_wp1_common_contracts.py`

Repository:
`python -m pytest -q`

The packet is deterministic and uses only Python standard-library runtime dependencies. Rollback is removal/forward supersession of the new inactive `opt_b.esl` common surfaces; no upstream object or selector is mutated.
