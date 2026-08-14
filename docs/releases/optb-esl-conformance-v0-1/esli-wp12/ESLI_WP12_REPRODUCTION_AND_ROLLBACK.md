# ESLI-WP12 reproduction and rollback

Targeted assurance:

```bash
PYTHONPATH=src:. python3 -m pytest tests/opt_b/esl/test_esli_wp12_read_models.py tests/opt_b/esl/test_esli_wp11_research_bridge.py tests/opt_b/esl/test_esli_wp10_c3_language.py -q
```

Repository assurance is the standard native pytest suite plus the maintained Research Console API surface, runner parity, pytest/unittest parity, FINAL_HEAD profile, SIQ READY and exact-final merge readiness.

Rollback before merge: abandon the bounded WP12 branch/PR. Rollback after merge: forward-supersede WP12 read-model-only artifacts while preserving WP0-WP11 identities/evidence. No rollback may introduce a frontend calculation path or governance/scientific write route.
