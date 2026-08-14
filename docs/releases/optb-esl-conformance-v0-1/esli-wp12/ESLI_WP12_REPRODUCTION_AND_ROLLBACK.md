# ESLI-WP12 reproduction and rollback

```bash
PYTHONPATH=src:. python3 -m pytest tests/opt_b/esl/test_esli_wp12_read_model.py tests/opt_b/esl/test_esli_wp11_research_bridge.py tests/opt_b/esl/test_esli_wp10_c3_language.py -q
```

Repository assurance uses the standard complete suite, Research Console maintained surface, runner parity, pytest/unittest parity, FINAL_HEAD profile, SIQ READY and exact-final merge readiness.

Rollback: forward-supersede WP12 read-model artifacts only. Preserve WP0-WP11 source objects and Console-owned UI. The read model is replaceable and never a scientific source of truth; no source record is mutated during rollback.
