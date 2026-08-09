# SRFDI-WP10 Execution Resilience Supersession Contract v0.1

## Purpose

Supersede **only** the process-level execution route that caused the authorized SRFDI-WP10 v0.6 attempt to become non-resumable after an external 600-second invocation termination. Preserve the frozen SRFD v0.4 scientific experiment, June population, source bindings, capacity envelope, family grid, preregistration, methods, thresholds, denominators and all authority firewalls unchanged.

## Governing incident

The single authorized v0.6 attempt consumed token `SRFD.JUNE.AUTH.3c63cd70ea57151a264443b436f94075bd8fb13f8a45f318a245cff96fefd168`, then terminated at the hosting invocation ceiling before the frozen T0 wall limit and before a lawful checkpoint receipt existed. That token remains `CONSUMED_NOT_REUSABLE`; partial family output remains `NONDISPOSITIONABLE`.

## Authority delta

`EXECUTION_RESILIENCE_ONLY`. This contract grants no market/scientific method authority and does not itself authorize a fresh June run. A fresh exact `SRFDI-G-JUNE-AUTH` remains required after this machinery passes assurance.

## Run-scoped authority rule

1. A fresh single-use token authorizes exactly one `run_id` bound to the exact frozen RunBinding.
2. Starting the run atomically emits one immutable `RunStartReceipt` and consumes the token for that run.
3. The same token can never start another run.
4. Process interruption does **not** create a new run. Continuation uses the existing `RunStartReceipt` plus the latest verified committed checkpoint.
5. Resume is therefore continuation of the already-authorized run, **not token reuse**.
6. Any change in population, eligible IDs, scientific manifest, preregistration, representation pack, segmentation pack, stability pack, source binding, capacity grid or implementation binding makes resume fail closed.

## Checkpoint constitution

A checkpoint is authoritative for restart only when all of the following are true:

- state is `COMMITTED`;
- it carries the same `run_id`, token ID and RunBinding hash as the immutable start receipt;
- its logical state hash and deterministic checkpoint identity verify;
- checkpoint sequence is contiguous;
- completed work-unit order is append-only and cannot be rewritten;
- every completed work unit has an output logical hash and, where external output exists, an artifact hash;
- the write was atomically committed. A `.tmp` or otherwise uncommitted file is ignored as authority;
- corruption, sequence gaps, binding drift or history rewrite fails closed.

## Work-unit granularity

The production WP10 execution route SHALL checkpoint at deterministic computational boundaries fine enough to survive a process invocation interruption without losing already committed work. The allowed hierarchy is:

`SEGMENTATION_STAGE -> COMPARABILITY_DOMAIN -> FAMILY_CONFIGURATION -> STABILITY/FAILURE-ATTRIBUTION_STAGE`.

The minimum family-grid restart unit is one deterministic family configuration within one comparability domain. The frozen grid contains 36 comparability domains and 1,944 family configurations. Computational subdivision is permitted only when it is scientifically lossless and equivalence-tested; it may not sample, alter a configuration, change a threshold, drop a method or change the population.

## Restart semantics

On restart, completed committed work units are skipped. The first uncommitted unit may be recomputed. No committed unit may be silently recomputed under a different implementation or binding. An incomplete output without a committed checkpoint has no restart authority.

## Required assurance before a fresh token

- uninterrupted synthetic run and interrupted/resumed synthetic run yield identical ordered work-unit output hashes;
- a token cannot be consumed twice;
- resume preserves the same `run_id`;
- binding drift fails closed;
- corrupt checkpoint fails closed;
- an uncommitted temporary checkpoint is ignored;
- completed units are not re-executed during resume;
- full repository and OVC profile/compatibility assurance pass at exact final head.

## Firewalls

Provider fetch remains `DENIED`. Validation 2025 remains `LOCKED_UNCONSUMED`. Scientific/method/representation/family/sensitivity promotion, selector mutation, canonical/R2 publication, probability, risk, exposure, trading and execution remain `NONE`.

## Exit

On PASS, the programme may prepare a fresh exact June authority token bound to this execution-resilience implementation and the unchanged frozen SRFD v0.4 experiment. The token is not issued by this contract.
