# RC-WP2-v0.3 — Overview Workspace and Ambient Health

## Disposition

`COMPLETE_RC_G2_V0_3_REVIEW_READY`

RC-WP2-v0.3 implements the deterministic Overview and ambient-health projection candidate authorised by RC-G1. The existing console remains fixture-only. The candidate is written to a replaceable local path and is not consumed by `Home.py` or `shell.py` before RC-G2.

## Implemented projection

The candidate projection contains:

- represented source commit and read-model logical hash;
- indexed-object, health-signal, release, gate, session and attention counts;
- seven stable ambient-health domains;
- source-bound release, gate and session summaries;
- consequence-aware attention items;
- a deterministic logical SHA-256 over canonical content.

The seven health domains are `DATA`, `READ_MODEL`, `ARTIFACTS`, `QA`, `RESEARCH_RECORDS`, `REPOSITORY` and `SEMANTIC`.

## Truth rules

- Missing signals never imply `PASS`.
- Unknown explicit health vocabulary fails closed to `BLOCK`.
- Research-record health remains `NOT_EVALUATED` with zero progress until the required schema, freeze, duplicate, cutoff and lineage assertions are represented.
- Lifecycle vocabulary such as `FROZEN`, `CLOSED` or `OBSERVATION_FROZEN` is not silently reinterpreted as health vocabulary.
- Every health domain names its consequence, affected surfaces and source references.
- An aggregate summary cannot conceal the individual domain states.

## Candidate build

```powershell
$env:PYTHONPATH = "src"
python scripts/build_research_console_overview.py `
  --read-model var/research_operations/read_model/current.json `
  --output var/research_operations/console/overview_candidate.json
```

The command prints `CANDIDATE_ONLY_PENDING_RC_G2`. The generated file is replaceable derived state and must not be committed as authority.

## Authority boundary

RC-WP2 implements projection code, schema, registry, fixture and tests only. Active live projection consumption remains denied pending RC-G2. Live Research surfaces remain denied pending RC-G3. Research writes remain separately gated.

Repository mutation, selector mutation, threshold mutation, release activation, market classification, probability, exposure, execution, agents and remote deployment remain denied.

## Verification target

RC-G2 must review determinism, source resolution, domain truth, degraded-state handling, candidate-path isolation and the exact activation boundary before the console may consume the projection.
