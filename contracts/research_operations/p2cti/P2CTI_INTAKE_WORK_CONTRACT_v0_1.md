# P2CTI Intake & Work Contract v0.1

Programme: `OVC-P2CTI-CONFORMANCE-v0.1`  
Packet: `P2CTII-WP5`  
Authority effect: **NONE**.

## Purpose

This contract defines deterministic synthetic/advisory machinery for `TheorySeed`, `IntakeTriage`, `WorkTicket`, `Deferral`, `Abandonment` and `Reentry` records. It does not activate durable continuous intake, create or rewrite a `TheoryRecord`, execute research work, form/freeze a candidate, or publish an operational current pointer.

## Source and identity

Every intake record MUST bind an exact source frontier and content-addressed control identity. A source reference carries source identity, source kind, locator, content SHA-256, authority references and an explicit `scientific_payload_copied=false`. Owner scientific payload is referenced, never copied.

Physical branch/PR/worker/run/cache identity is non-semantic and MUST NOT enter logical identity.

## Intake triage

Triage reuses the governing DMRP Path-2 intake vocabulary. Exact registered mappings MAY be projected; unmapped values remain `UNMAPPED_REVIEW_REQUIRED` with their registered review action. Silent coercion is forbidden.

`FORMALISE_NOW` is only a bounded pre-evidence readiness routing to `READY_FOR_GUIDED_FORMALISATION`; it does not freeze theory or preregister/execute an experiment. `DEFER` and `DESCRIPTIVE_LANGUAGE_ONLY` retain their registered meanings.

## Work machinery

Work tickets are operational records only. `work_class` and `work_state` come from the closed P2CTI operational registry. Queue ordering is deterministic and non-scientific. Queue age, effort and operator touches are telemetry; they are not scores, quotas, scientific value, priority authority or promotion criteria.

Deferral, abandonment and re-entry are append-only control records. Abandonment MUST preserve evidence and MUST NOT delete or rewrite owner scientific records.

## Non-transitivity and denied effects

The machinery MUST carry `authority_effect=NONE`, `write_activation=false`, `scientific_effect=NONE`, and `candidate_effect=NONE`. It MUST reject decision-bearing fields for probability, risk, exposure, trade/execution, candidate freeze, theory truth/value/alpha or similar downstream authority.

Before `P2CTII-G-OBSERVABILITY-ACTIVATE`, outputs remain synthetic/read-only/advisory. Durable intake writes remain denied before `P2CTII-G-CONTINUOUS-INTAKE`.
