# ESLI-WP6 reproduction and rollback

Packet: `ESLI-WP6`  
Gate: `ESLI-G6`  
Initial baseline: `d392c4572e539a399e461212b4991db55ae46477`  
Current reconciled baseline: `d41a29f9895482de0d1515efc2ca0aebf8016b45`  
Branch: `build/esli-wp6-soi-compatibility-20260813-requeue1`  
Authority delta: `NONE`.

The initial PR #728 candidate `25f4453b67435761ede4d1011119ad7aff33e148` passed the repository suite, pytest/unittest parity, runner parity and FINAL_HEAD/profile assurance. Serialized merge readiness was correctly withheld while GRT2 predecessor PR #726 held the final-PASS lease; #726 then merged and advanced `main` to `d41a29f9895482de0d1515efc2ca0aebf8016b45`. WP6 was rebuilt directly from that lawful main with no force-push, history rewrite or contract weakening.

## Targeted reproduction

```bash
PYTHONPATH=src python3 -m unittest discover -s tests/opt_b/esl -p 'test_esli_wp6_soi_compat.py' -v
PYTHONPATH=src python3 -m unittest discover -s tests/opt_b/esl -p 'test_esli_wp6_fixture_identity.py' -v
PYTHONPATH=src python3 -m unittest discover -s tests/opt_b/esl -p 'test_soi_maturity_fail_closed.py' -v
PYTHONPATH=src python3 -m unittest discover -s tests/opt_b/esl -p 'test_esli_wp5_sri_compat.py' -v
PYTHONPATH=src python3 -m unittest discover -s tests/opt_b/sfc -p 'test_sfc_wp4_fdi.py' -v
```

Then run the repository-complete suite, runner parity, pytest/unittest parity, FINAL_HEAD profile assurance and serialized stable-main merge readiness against one pinned candidate.

## Deterministic assertions

- The topology registry and its paired schema contain exactly `FAMILY`, `HIERARCHY`, `OVERLAP`, `GRAPH`, `CONTINUUM`, and `COMPOSITION`.
- Only `FAMILY` is `EXECUTABLE_INACTIVE`; it adapts one exact preserved SFC `FamilyCatalog` and never invokes a discovery algorithm.
- The other five topologies are `INTERFACE_ONLY`; invocation fails with `SOI_ADAPTER_NOT_MATERIALIZED:<topology>` and emits no empty or placeholder result.
- The permanent IAV-03 regression rejects an attempted `GRAPH` executable relabelling.
- Source catalog, family and assignment hashes are verified under the SFC source serializer.
- Family records, ambiguity, residual, noise, singleton, not-comparable and not-evaluable states remain explicit.
- The family-present and no-stable-family fixtures carry distinct exact SFC configuration/catalog identities.
- `NO_STABLE_FAMILY` is scoped to `FAMILY` and cannot become `NO_STABLE_ORGANISATION`.
- Topology and source method identity remain separate.
- No topology/method/family/scientific/semantic/Validation/publication/probability/risk/exposure/execution authority is created.

## Rollback

WP6 is additive and has no data migration or active selector. A forward revert/supersession may remove the SOI contract, schemas, topology registry, FAMILY adapter manifest, implementation, fixtures, tests and WP6 records while leaving:

- ESLI-WP0 through ESLI-WP5 unchanged;
- `OVC-SFC-v0.1` completed/preserved and its exact `FamilyCatalog` identities addressable;
- all existing FDI/SRFD implementation and historical evidence unchanged;
- active topology, method, family, semantic and Validation authority unchanged (`NONE` / `LOCKED_UNCONSUMED`).

No force-push, history rewrite, provider action, Validation access or publication is part of rollback.
