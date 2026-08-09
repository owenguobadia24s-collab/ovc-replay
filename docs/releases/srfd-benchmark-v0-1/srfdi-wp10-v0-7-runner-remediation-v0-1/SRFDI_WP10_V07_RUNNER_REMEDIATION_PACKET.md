# SRFDI-WP10 v0.7 Runner Remediation Packet

Status: `IMPLEMENTATION_CANDIDATE_PENDING_EXACT_HEAD_ASSURANCE_AND_MERGE`

The operator approved `OVC APPROVE WP10 v0.7 runner remediation`. The remediation is execution-route only: frozen v0.4 science, source population, 36 comparability domains, 1,944 family configurations, segmentation specification, stability rules, provider-fetch denial and Validation lock remain unchanged.

## Runtime candidate

The candidate adds:

- `wp10_durable_execution.py` — atomic external artifact commitment before checkpoint commitment, artifact verification on resume, external-volume enforcement and portable RSS telemetry;
- `wp10_v07_contract.py` — frozen source/population/scientific binding checks and deterministic source reconstruction;
- `wp10_v07_family.py` — exact reusable domain preparation plus one-family-configuration materialization with identity equivalence to the frozen full-grid constructor;
- `wp10_v07_analysis.py` — capacity-safe exact invariant-core and method-disagreement evidence plus frozen v0.4 stability/correspondence materialization;
- `wp10_v07_runner.py` — preflight-first production orchestration, exact 1,944-configuration checkpoint granularity, two executable frozen segmentation methods and evidence-packet construction.

The runner does not import the historical Unix-only `resource` dependency at module import time. Windows peak RSS uses `GetProcessMemoryInfo`; POSIX uses the standard-library `resource` module lazily.

## Candidate implementation binding

`registries/research/srfd/wp10_v07_runner_implementation_binding_candidate_v0_1.json`

Logical SHA-256:

`1253dbde8280d7649da9f68e876f453929eab4a3bbf1a338a4c900c26371c3b7`

Runtime Git blobs:

- existing resilience primitive: `073772c33f39afc63d8194d34e798aa3dbc9b61b`
- durable execution: `f1afc8b23a229aacf15da8f0d53fda70b46ae1c9`
- frozen contract runtime: `1a140e544cfd7d74a90c980198eb1abe0186e1ec`
- family runtime: `63453b7ff88d8351eaeeeb1d2fbfe8189f76795b`
- analysis runtime: `4dd3e64b1041031e49cb81ddffe012e642f42b28`
- production runner: `47fbf10aeb7ba41ee91cd8638650522401fad82a`

The family-runtime correction preserves the frozen non-PAM `FamilyMethodSpec.max_iterations=20` identity while PAM remains fixed at 8. This is required for byte/logical identity equivalence with the already-frozen full-grid constructor; it changes no family membership algorithm or scientific parameter.

## Assurance already established before latest-main reconciliation

On candidate head `de245633e1c195220dda4dda20e2a18fea3123ad`:

- complete repository suite: `PASS`;
- OVC tiered compatibility shadow: `PASS`;
- unresolved review threads: `0`;
- durable interruption/resume, orphan-artifact recovery, corruption fail-closed and external-quota tests: `PASS`;
- exact 54 configurations per domain / 1,944 configuration work units: `PASS`;
- split per-configuration materialization against frozen full-grid reference: `PASS`;
- optimized invariant-core and method-disagreement against frozen reference semantics: `PASS`;
- scientific RunBinding drift rejection and preflight-before-token-consumption controls: `PASS`.

Current `main` advanced through unrelated IROF governance work after the candidate was built. The PR therefore requires one final no-force reconciliation to latest lawful `main`, followed by fresh exact-head CI before merge.

## Authority and token interlock

Current v0.7 token:

`SRFD.JUNE.AUTH.baad8aa9752b789cea06f41c3bc134e86711a257f1219d04b4034a664a8f1ef5`

State during remediation: `AUTHORIZED_UNCONSUMED_DO_NOT_START_DURING_REMEDIATION`.

It MUST NOT be consumed under the remediated runner because its historical RunBinding predates the production runner. After merge and exact-head assurance, preserve that token as `SUPERSEDED_UNUSED_UNCONSUMED`, then construct one fresh exact runner-bound token only under the already-merged standing remaining-sequence delegation and only if that delegation still authorizes the action at current court record.

## Firewalls

- provider fetch: `DENIED`;
- Validation 2025: `LOCKED_UNCONSUMED`;
- selector/family/semantic/scientific promotion: `NONE`;
- canonical/R2 publication: `NONE`;
- probability/risk/exposure/trading/execution: `NONE`.
