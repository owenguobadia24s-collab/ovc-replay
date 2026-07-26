# OVC Research Console v0.2 UI Authority Contract

Document ID: OVC-RESEARCH-CONSOLE-UI-AUTHORITY-CONTRACT.v0.2
Status: FROZEN_BY_RC_00_PENDING_RC_G0_REVIEW
Baseline commit: e365eddb2ee465312ed6563cbe6df0760661f0d7
Branch: build/research-console-v0-2-preflight-rc00

## Purpose

Freeze the authority, route, control, source and fallback boundaries for the Research Console v0.2 interface before visual implementation begins.

## Authority

The console is a local, replaceable, derived read surface. It may inspect approved repository records, external-artifact catalogue references, releases, QA assertions, gate decisions and research records through a deterministic typed read model.

It may not:

- mutate repository files, branches, commits or pull requests;
- change release lifecycle, selectors, thresholds or parameter packs;
- create or override market classifications;
- create probability, setup, risk, exposure, trading or execution objects;
- self-approve gates, releases, records or changes;
- deploy, host remotely or bind to a non-local interface by default;
- traverse repository or external-artifact trees during a Streamlit rerun;
- treat missing or absent health evidence as PASS.

## Persistent authority boundary

| Field | Value |
|---|---|
| mode | READ_ONLY |
| repository_mutation | NONE |
| selector_mutation | NONE |
| threshold_mutation | NONE |
| market_classification | NONE |
| probability | NONE |
| exposure | NONE |
| execution | NONE |
| agent | NONE |
| deployment | LOCAL_ONLY |

The compact authority strip may summarize these values. The complete machine-readable boundary must remain inspectable.

## Source rule

Every displayed claim, summary, status or count must resolve to one or more immutable source references. Presentation projections never gain more authority than their source objects.

Approved source families:

- ResearchReadModel and ReadModelNode objects;
- artifact catalogue nodes and issues;
- approved release registries, descriptors and selectors;
- QA runs, assertions, gate packets and operator decisions;
- research records and audit events;
- bounded local configuration resolved by the launcher.

Pages must not open arbitrary paths supplied by UI input. Local files may be opened only through catalogue or registry metadata and path-safety rules.

## Health truth rule

ALL_CLEAR or PASS may be displayed only when every required domain has a current explicit PASS assertion or a documented NOT_APPLICABLE result. No signals, missing inputs, stale indexes and unresolved sources are NOT_EVALUATED, INCOMPLETE, WARN or BLOCK as defined by the status registry.

## Route and control rule

Every route and visible action must appear in the frozen route and action registries. Unregistered routes or controls are prohibited. Deferred controls must be disabled or omitted and must state the authority needed for activation.

## Local runtime rule

The supported launcher must:

1. require the exact represented repository commit;
2. build and validate the read model before starting the UI;
3. fail closed on invalid schema, hash or required-domain blockers;
4. bind Streamlit to 127.0.0.1;
5. expose the represented commit and read-model hash persistently.

## Empty-state rule

An empty surface must state whether it is EXPECTED_EMPTY, NOT_MATERIALIZED, MISSING_SOURCE, STALE, BLOCKED, NOT_EVALUATED or NOT_APPLICABLE. A polished empty panel must never imply successful system health.

## Change control

Any change to route authority, action authority, status meaning, health truth, source allowlist, local binding or deferred-write treatment requires a new contract version and a fresh gate review.

## RC-00 exit condition

RC-00 is complete when the baseline, this contract and all five UI registries are committed atomically. RC-G0 remains PENDING_OPERATOR_REVIEW until the exact branch result is independently reviewed and accepted.
