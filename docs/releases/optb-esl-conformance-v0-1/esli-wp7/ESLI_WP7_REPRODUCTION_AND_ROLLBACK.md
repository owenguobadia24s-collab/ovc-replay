# ESLI-WP7 reproduction and rollback

Baseline: `69368a5e3eac1c7c79455d6abeb4786cceb51d74`  
Branch: `build/esli-wp7-organisation-evidence-requeue-20260813`  
Authority delta: `NONE`.

Reconstructed from preserved PR #738 onto the latest lawful main. Prior PR #738, branch `build/esli-wp7-organisation-evidence-20260813`, and head `19840eca2268d8a882aff810042e45fbe370a547` remain preserved evidence.

## Targeted reproduction

```bash
PYTHONPATH=src python3 -m unittest discover -s tests/opt_b/esl -p 'test_esli_wp7_organisation_evidence.py' -v
PYTHONPATH=src python3 -m unittest discover -s tests/opt_b/esl -p 'test_esli_wp6_soi_compat.py' -v
PYTHONPATH=src python3 -m unittest discover -s tests/opt_b/sfc -p 'test_sfc_wp4_fdi.py' -v
```

Final assurance also requires repository-wide tests, Research Console maintained surface, runner parity, pytest/unittest parity, FINAL_HEAD profile assurance and serialized stable-main readiness.

## Rollback

Forward-supersede or revert WP7-only artifacts. Preserve WP0-WP6, prior PR #738, SFC/SOI evidence and Git history.
