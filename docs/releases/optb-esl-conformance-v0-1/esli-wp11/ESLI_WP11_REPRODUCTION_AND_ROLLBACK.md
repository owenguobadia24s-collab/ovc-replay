# ESLI-WP11 reproduction and rollback

```bash
PYTHONPATH=src:. python3 -m pytest tests/opt_b/esl/test_esli_wp11_research_bridge.py tests/opt_b/esl/test_esli_wp10_c3_language.py tests/opt_b/esl/test_esli_wp9_term_qualification.py -q
```

Repository assurance uses the standard complete suite, Research Console maintained surface, parity checks, FINAL_HEAD profile, SIQ READY and exact-final merge readiness.

Rollback: forward-supersede WP11 bridge-only artifacts. Preserve WP0-WP10, Research Operations records, DMRP identities and all historical evidence. Do not create or delete ResearchCandidateGeneration objects as rollback.
