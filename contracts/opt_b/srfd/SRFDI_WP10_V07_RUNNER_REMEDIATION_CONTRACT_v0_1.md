# SRFDI-WP10 v0.7 Production Runner Remediation Contract v0.1

## Purpose

Implement the missing production execution route required to run the already-frozen SRFDI-WP10 v0.7 June experiment safely on a local durable workspace. This remediation is **execution-route only**. It does not change the frozen v0.4 scientific experiment, source, 8,598-record population, representation grid, distance rule, family methods, parameter ladders, segmentation specification, stability metrics, denominators, capacity envelope, or scientific disposition rules.

## Operator approval

The operator instruction `OVC APPROVE WP10 v0.7 runner remediation` authorizes construction, assurance and merge of this execution-only remediation. It does **not** authorize consumption of the currently unused v0.7 token under a different implementation binding.

## Governing run-safety rule

The current v0.7 token remains immutable and unconsumed during remediation. Because it binds the pre-remediation implementation, it MUST NOT start a run after this remediation becomes effective. After merge and exact-head assurance, it must be preserved as `SUPERSEDED_UNUSED_UNCONSUMED`, and a fresh exact token must be minted under the standing remaining-sequence delegation before June execution.

## Required implementation

1. Add a durable external artifact store. Every completed work unit writes canonical bytes atomically before checkpoint commitment. The checkpoint carries both output logical hash and artifact SHA-256.
2. Resume verifies every committed artifact before skipping completed work. Missing, corrupt, rewritten, or binding-mismatched artifacts fail closed.
3. Preserve the existing one-token/one-run `RunStartReceipt` and same-run resume semantics.
4. Add a production WP10 runner that performs all source and durable-workspace checks before token consumption.
5. The family-grid restart unit MUST be one exact family configuration inside one comparability domain. The frozen 36-domain / 1,944-configuration grid may not be collapsed to a domain-only checkpoint.
6. Domain preparation may persist exact reusable traces/cores, but each of the 1,944 family catalogs is separately materialized, persisted and checkpointed.
7. Execute only the frozen segmentation methods marked executable: `RUN_CHANGE_SEGMENTATION` and `NULL_BOUNDARY_CONTROL`. Preserve the three declared nonexecuted methods and their exact reason codes.
8. Materialize the exact v0.4 stability/correspondence/invariant/method-disagreement evidence without selecting a winner or performing G10/G11 scientific disposition inside the runner.
9. Enforce the frozen T0 external artifact ceiling and portable peak-RSS telemetry without introducing a new scientific dependency.
10. The runner must be Windows-portable and must not depend on the Unix-only `resource` module at import time.

## Frozen bindings

- population: `SRFD.POP.6efa7dd55636d036c12e580e0793abacf8c805bcf6d77bb6e2edf7cffbc113bd`
- eligible count: `8598`
- eligible IDs SHA-256: `fbb03d1db6cfa91f63330433e835c2bd659d1128b682817083d6f7af9f2aca4e`
- comparability domains: `36`
- exact pair opportunities: `35,380,668`
- family configurations: `1,944`
- provider fetch: `DENIED`
- Validation 2025: `LOCKED_UNCONSUMED`
- T0 wall ceiling: `14,400s`
- T0 peak RSS ceiling: `17,179,869,184 bytes`
- T0 external artifact ceiling: `10,737,418,240 bytes`

## Firewalls

No selector change, family/representation/semantic promotion, canonical or R2 publication, probability, risk, exposure, trading or execution authority is granted. No provider data may be fetched and Validation 2025 may not be accessed.

## Exit

The remediation exits only after exact-head repository assurance and OVC compatibility/merge-readiness pass. Then preserve the current v0.7 token as unused historical authority, mint one fresh implementation-bound token under the existing standing delegation, and only then start or resume WP10.
