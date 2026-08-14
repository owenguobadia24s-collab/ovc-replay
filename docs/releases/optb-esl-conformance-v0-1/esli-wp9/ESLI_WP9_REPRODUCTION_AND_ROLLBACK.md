# ESLI-WP9 reproduction and rollback

Reproduce targeted assurance:

```bash
PYTHONPATH=src:. python3 -m pytest tests/opt_b/esl/test_esli_wp9_term_qualification.py tests/opt_b/esl/test_esli_wp8_cei.py tests/opt_b/esl/test_esli_wp7_organisation_evidence.py -q
```

Repository assurance is the standard native pytest suite plus Research Console maintained API surface, runner parity, pytest/unittest parity, FINAL_HEAD profile, SIQ READY and exact-final merge readiness.

Rollback before merge: abandon the bounded WP9 branch/PR. Rollback after merge: forward-supersede WP9-only term-qualification contracts, schemas, registry, fixture and implementation while preserving WP0-WP8 history and all WP9 evidence. Never rewrite historical term generations or active semantic authority.
