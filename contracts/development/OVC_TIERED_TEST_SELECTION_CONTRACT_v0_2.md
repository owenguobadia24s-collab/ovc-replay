# OVC Tiered Blocking Assurance Contract v0.2

## Authority and supersession

This contract is activated by the operator instruction of 2026-09-07 to make the selected tiered profile the ordinary per-packet blocking assurance and to reserve the complete legacy/canonical sweep for final-head, scheduled, assurance-harness-change or risk-triggered execution. It supersedes the ordinary-blocking rule in v0.1 without rewriting v0.1 or any historical evidence produced under it.

The authority delta is limited to test-orchestration policy. It grants no scientific, semantic, selector, publication, Validation, probability, risk, exposure, trading, execution, repository-bot write, direct-main write, force-push or history-rewrite authority.

## Profiles

| Profile | Ordinary use | Blocking effect |
|---|---|---|
| `FAST` | Documentation-only or bounded non-executable packet surfaces. | The fresh remote FAST profile, VIT routing and exact-final SIQ/GRT materialisation controls block the packet. |
| `PACKET` | Ordinary packet contracts, schemas, registries, fixtures, source, scripts, tests and court records. | Changed packet tests, syntax/data validation, retained authority checks, VIT routing and exact-final SIQ/GRT materialisation controls block the packet. |
| `FINAL_HEAD` | Unknown paths, test/assurance harness changes, shared workflow/CLI changes or explicit risk escalation. | The complete canonical pytest sweep, legacy unittest-under-pytest parity, runner parity and the tiered profile all block. |
| `GATE_REPLAY` | Reproduction of a named frozen gate command. | Additional evidence only; it cannot substitute for the triggered complete sweep. |

Profile order remains `FAST < PACKET < FINAL_HEAD`. Unknown or ambiguous scope fails closed to `FINAL_HEAD` or `BLOCK` respectively.

## Ordinary packet assurance

For a `FAST` or `PACKET` manifest:

1. `OVC profile assurance` is the normal base-independent blocking check.
2. `VIT routing preflight` must pass freshly on the exact candidate head.
3. `PACKET` executes every changed `tests/**/test*.py` file. A changed executable `src/**` or `scripts/**` path without at least one changed packet test fails closed.
4. Python and JSON mutations receive deterministic syntax/data validation before packet tests.
5. Authority-boundary tests remain retained for `PACKET`.
6. SIQ READY, one-writer late placement, GRT and post-write tree equality remain unchanged.

Passing local tests never substitutes for the fresh remote tiered profile.

## Complete-sweep triggers

The complete sweep is mandatory for:

- `FINAL_HEAD` selection, including unknown or risk-classified paths;
- any pytest collection or assurance-harness mutation;
- scheduled reference runs;
- pushes to `main` as the final-head reference;
- explicit manual final-head or gate-replay execution.

Only these runs execute `pytest-unittest-parity`. The parity harness is retained, versioned and runnable; it is removed only from the ordinary `FAST`/`PACKET` blocking path.

## Equivalence qualification

The retirement from ordinary blocking is permitted only while all of the following remain true:

- canonical pytest collection proves every unittest-discovered item is present;
- the canonical shard union is exact, duplicate-free and includes pytest-native items;
- historical and cutover qualification show the complete canonical suite and legacy surface agree on outcome;
- any mutation to pytest configuration, collection hooks, the parity harness, shard harness, workflow or test dependencies triggers the complete sweep;
- divergence, missing collection members or an unevaluable manifest fails closed to `FINAL_HEAD`.

The repository qualification packet records the bound population and hashes for the activation baseline.

## Rollback

Forward-revert the v0.2 workflow/registry pointer to v0.1 behaviour and restore `pytest-unittest-parity` plus the complete canonical suite as ordinary per-packet prerequisites. Preserve v0.2 evidence and Git history.
