# ESLI-WP5 reproduction and rollback

Packet: `ESLI-WP5`  
Gate: `ESLI-G5`  
Initial implementation baseline: `36505abca85c9532d4660a7656dde899862e864b`  
Current reconciled baseline: `93ae535afff7dadec17b97e064d0b0e01a95bcef`  
Evaluated implementation candidate: `267883e8cc87181f5fcea6524dababcd3e782f94`  
Authority delta: `NONE`.

The initial candidate was intentionally superseded after the stable-main guard observed CI-only main movement through #714. No implementation contract was weakened; the candidate was rebuilt directly from the new lawful main.

## Targeted reproduction

```bash
PYTHONPATH=src python3 -m unittest discover -s tests/opt_b/esl -p 'test_esli_wp5_sri_compat.py' -v
PYTHONPATH=src python3 -m unittest discover -s tests/opt_b/esl -p 'test_esli_wp1_common_contracts.py' -v
PYTHONPATH=src python3 -m unittest discover -s tests/opt_b/esl -p 'test_esli_wp3_occurrence_compiler.py' -v
```

Exact-head repository assurance for candidate `267883e8...`:
- tests run `31687577441`, repository job `94407231466`: PASS;
- runner parity `94407231420`: PASS;
- pytest/unittest parity `94407231434`: PASS;
- final integration admission `94407149510`: PASS;
- tiered run `31687577372`, profile assurance `94407149476`: PASS;
- serialized merge readiness `94407149613`: PASS.

## Deterministic assertions

The WP5 fixture binds one explicit inactive SRI-R8 compatibility pack. Reordering source facets preserves exact output identity. Changing pack/comparability generation changes identity. Missing/NOT_EVALUABLE facets remain typed and null; no fill/imputation occurs. Historical SFC/SRFD aliases are crosswalk references only and never identity equivalence.

## Rollback demonstration

WP5 is additive and contains no data migration or active selector. A forward revert/supersession may remove the new ESL SRI adapter, contract/schema/manifest/crosswalk/fixture/tests and WP5 release records while leaving:

- StructuralOccurrence/EvidenceFrontier and WP0-WP4 unchanged;
- `src/ovc/opt_b/sfc` and `src/ovc/opt_b/srfd` historical implementations unchanged;
- all historical representation IDs and evidence addressable;
- active representation/method/family/semantic authority unchanged (`NONE`).

No force-push, history rewrite, provider action, Validation access or publication is part of rollback.
