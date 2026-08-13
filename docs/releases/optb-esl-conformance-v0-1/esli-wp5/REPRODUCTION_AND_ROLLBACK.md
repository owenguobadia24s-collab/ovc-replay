# ESLI-WP5 reproduction and rollback

Packet: `ESLI-WP5`  
Gate: `ESLI-G5`  
Baseline: `36505abca85c9532d4660a7656dde899862e864b`  
Authority delta: `NONE`.

## Targeted reproduction

```bash
PYTHONPATH=src python3 -m unittest discover -s tests/opt_b/esl -p 'test_esli_wp5_sri_compat.py' -v
PYTHONPATH=src python3 -m unittest discover -s tests/opt_b/esl -p 'test_esli_wp1_common_contracts.py' -v
PYTHONPATH=src python3 -m unittest discover -s tests/opt_b/esl -p 'test_esli_wp3_occurrence_compiler.py' -v
```

The repository-required CI then supplies the complete suite, runner parity, pytest/unittest parity, FINAL_HEAD/profile assurance and serialized stable-main readiness on the exact candidate SHA.

## Deterministic assertions

The WP5 fixture binds one explicit inactive SRI-R8 compatibility pack. Reordering source facets must preserve the exact output ID. Changing pack identity or comparability generation must change it. Missing/NOT_EVALUABLE facets stay typed and null; no fill/imputation occurs. Historical SFC/SRFD aliases remain crosswalk references only.

## Rollback demonstration

WP5 is additive and contains no data migration or active selector. A forward revert/supersession may remove the new ESL SRI adapter, contract/schema/manifest/crosswalk/fixture/tests and WP5 release records while leaving:

- StructuralOccurrence/EvidenceFrontier and WP0-WP4 unchanged;
- `src/ovc/opt_b/sfc` and `src/ovc/opt_b/srfd` historical implementations unchanged;
- all historical representation IDs and evidence addressable;
- active representation/method/family/semantic authority unchanged (`NONE`).

No force-push, history rewrite, provider action, Validation access or publication is part of rollback.
