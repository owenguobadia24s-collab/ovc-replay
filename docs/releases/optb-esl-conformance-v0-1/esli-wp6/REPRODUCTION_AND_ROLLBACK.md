# ESLI-WP6 reproduction and rollback

Packet: `ESLI-WP6`  
Gate: `ESLI-G6`  
Current reconciled baseline: `45146c31641d719dbfb73dbcd51a75ec2a9d7e19`  
Branch: `build/esli-wp6-soi-compatibility-20260813-requeue2`  
Authority delta: `NONE`.

## Reconciliation history

The initial PR #728 candidate passed repository/parity/profile assurance but was superseded after predecessor PR #726 advanced `main`. PR #734 then reproduced the implementation on `d41a29f9`, passed exact-head assurance and materialised delegated G6 evidence, but was closed unmerged to release the serialized final-integration lane for systemic required-check repair PR #732. PR #732 squash-merged as `45146c31641d719dbfb73dbcd51a75ec2a9d7e19`. This candidate is rebuilt directly from that lawful main with no force-push, history rewrite, scope expansion or contract weakening.

## Targeted reproduction

```bash
PYTHONPATH=src python3 -m unittest discover -s tests/opt_b/esl -p 'test_esli_wp6_soi_compat.py' -v
PYTHONPATH=src python3 -m unittest discover -s tests/opt_b/esl -p 'test_esli_wp6_fixture_identity.py' -v
PYTHONPATH=src python3 -m unittest discover -s tests/opt_b/esl -p 'test_soi_maturity_fail_closed.py' -v
PYTHONPATH=src python3 -m unittest discover -s tests/opt_b/esl -p 'test_esli_wp5_sri_compat.py' -v
PYTHONPATH=src python3 -m unittest discover -s tests/opt_b/sfc -p 'test_sfc_wp4_fdi.py' -v
```

The final candidate must also pass the repository-complete suite including the exact Research Console surface, runner parity, pytest/unittest parity, FINAL_HEAD profile assurance and serialized stable-main merge readiness.

## Deterministic assertions

- The topology registry and paired schema contain exactly `FAMILY`, `HIERARCHY`, `OVERLAP`, `GRAPH`, `CONTINUUM`, and `COMPOSITION`.
- Only `FAMILY` is `EXECUTABLE_INACTIVE`; it adapts one exact preserved SFC `FamilyCatalog` and never invokes a discovery algorithm.
- The other five topologies are `INTERFACE_ONLY`; invocation fails with `SOI_ADAPTER_NOT_MATERIALIZED:<topology>` and emits no empty or placeholder result.
- Permanent IAV-03 assurance rejects attempted executable relabelling of an interface-only topology.
- Source catalog, family and assignment hashes are verified under the SFC source serializer.
- Family records, ambiguity, residual, noise, singleton, not-comparable and not-evaluable states remain explicit.
- The family-present and no-stable-family fixtures carry distinct exact SFC configuration/catalog identities.
- `NO_STABLE_FAMILY` is scoped to `FAMILY` and cannot become `NO_STABLE_ORGANISATION`.
- Topology and source method identity remain separate.
- No topology/method/family/scientific/semantic/Validation/publication/probability/risk/exposure/execution authority is created.

## Rollback

WP6 is additive and has no data migration or active selector. A forward revert/supersession may remove the SOI contract, schemas, topology registry, FAMILY adapter manifest, implementation, fixtures, tests and WP6 records while leaving ESLI-WP0 through ESLI-WP5 and all SFC/FDI/SRFD identities/evidence unchanged. No force-push, history rewrite, provider action, Validation access or publication is part of rollback.
