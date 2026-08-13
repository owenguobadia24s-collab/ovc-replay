# ESLI-WP7 reproduction and rollback

Baseline: `e03823decfdc9984cdc2fdc25a030437e7337ef5`  
Branch: `build/esli-wp7-organisation-evidence-requeue4-20260813`  
Authority delta: `NONE`.

Reconstructed from the already-bounded WP7 implementation onto the latest lawful main. Prior PR #738 / head `19840eca2268d8a882aff810042e45fbe370a547` and PR #758 / head `0a041712426bcda09bbbe003b77f14b1eedc4384`, including their branches, CI and review evidence, remain preserved. Unmutated abandoned requeue branches are also retained without history rewrite.

## Targeted reproduction

```bash
PYTHONPATH=src python3 -m unittest discover -s tests/opt_b/esl -p 'test_esli_wp7_organisation_evidence.py' -v
PYTHONPATH=src python3 -m unittest discover -s tests/opt_b/esl -p 'test_esli_wp6_soi_compat.py' -v
PYTHONPATH=src python3 -m unittest discover -s tests/opt_b/sfc -p 'test_sfc_wp4_fdi.py' -v
```

Final assurance also requires repository-wide tests, Research Console maintained surface, runner parity, pytest/unittest parity, FINAL_HEAD profile assurance and serialized stable-main readiness.

## Rollback

Forward-supersede or revert WP7-only artifacts. Preserve WP0-WP6, prior PR #738/#758, SFC/SOI evidence and Git history.
