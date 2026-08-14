# ESLI-WP10 reproduction and rollback

Targeted assurance:

```bash
PYTHONPATH=src:. python3 -m pytest tests/opt_b/esl/test_esli_wp10_c3_language.py tests/opt_b/esl/test_esli_wp9_term_qualification.py tests/opt_b/esl/test_esli_wp4_c3_reference.py -q
```

Repository assurance is the standard native pytest suite plus Research Console maintained API surface, runner parity, pytest/unittest parity, FINAL_HEAD profile, SIQ READY and exact-final merge readiness.

Rollback before merge: abandon the bounded WP10 branch/PR. Rollback after merge: forward-supersede WP10-only C3 ESL conformance artifacts while preserving WP0-WP9 history, inactive reference semantics and all WP10 evidence. Never activate C3, rewrite historical ASTs or admit active vocabulary as rollback.
