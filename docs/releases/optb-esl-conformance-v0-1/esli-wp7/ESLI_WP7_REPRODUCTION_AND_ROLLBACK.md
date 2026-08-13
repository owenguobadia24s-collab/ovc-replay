# ESLI-WP7 reproduction and rollback

Baseline: `a0bb73cf6026e7f67d73f431636c3568e42e7040`  
Branch: `build/esli-wp7-organisation-evidence-20260813`  
Authority delta: `NONE`.

## Targeted reproduction

```bash
PYTHONPATH=src python3 -m unittest discover -s tests/opt_b/esl -p 'test_esli_wp7_organisation_evidence.py' -v
PYTHONPATH=src python3 -m unittest discover -s tests/opt_b/esl -p 'test_esli_wp6_soi_compat.py' -v
PYTHONPATH=src python3 -m unittest discover -s tests/opt_b/sfc -p 'test_sfc_wp4_fdi.py' -v
```

Final assurance also requires the repository-complete suite, exact Research Console maintained surface, runner parity, pytest/unittest parity, FINAL_HEAD profile assurance and serialized stable-main merge readiness.

## Deterministic assertions

- every metric identifies eligible universe, numerator, denominator, exclusions and missingness;
- zero denominator is `NOT_EVALUABLE`, never fabricated zero support;
- correspondence and invariants preserve endpoint identities;
- disagreement is typed by one explicit axis and is not collapsed to a universal score;
- raw view output is distinct from scientific support;
- `NO_STABLE_FAMILY` remains FAMILY-scoped;
- `NO_STABLE_ORGANISATION` requires all six topologies, a complete evaluable envelope and a separately authorised executable rule pack;
- WP7 decision-rule maturity is `INTERFACE_ONLY`;
- reserved scientific, semantic, Validation, publication and exposure fields fail closed.

## Rollback

Forward-supersede or revert the WP7-only contract, schema, registries, implementation, fixture, tests and records. Preserve exact WP0-WP6 records, SFC catalogues, SOI view identities and Git history.
