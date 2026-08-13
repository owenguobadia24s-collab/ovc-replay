# OVC Plan/Packet Materialisation Contract v0.1

Status: IMPLEMENTATION CONTRACT — bounded by DSAI-PPM-G0  
Programme: OVC-DSAI-PPM-v0.1  
Authority effect: NONE

## 1. Purpose and boundary

This contract defines the deterministic bridge from an operator-reviewed OVC implementation-plan transcription to the existing Development Skills Architecture (DSAI) packet/orchestration records.

The bridge is deliberately mechanical. It does **not** parse or interpret DOCX prose, invent missing work-packet semantics, resolve Skill releases, activate capabilities, or grant authority. A human-governed plan remains the source; the materialisation is a bound machine representation of an already reviewed transcription.

Pipeline:

`PlanSourceRef -> ProgrammeManifest -> PacketManifest[] + CapabilityRequirement[] + PacketGateManifest[] -> existing PacketGraphSnapshot -> MaterialisationReceipt`

The existing DSAI packet-eligibility and capability-resolution layers remain the consumers. This contract does not fork them.

## 2. Source binding

Every materialisation MUST bind:
- exact `plan_id`;
- exact `plan_version`;
- repository/external `source_ref`;
- lowercase SHA-256 of the governing source bytes/text.

`PlanSourceRef.source_ref_id` is a canonical role-bound hash of those logical fields. If source bytes are supplied during materialisation, their SHA-256 MUST equal the declared source hash or materialisation fails.

A later execution MAY proceed only while the current governing-source hash equals both the PlanSourceRef hash and the MaterialisationReceipt hash. Drift is `NOT AUTHORISED` until a new reviewed materialisation is produced.

## 3. Programme and packet representation

`ProgrammeManifest` MUST contain:
- programme identity;
- plan identity/version/source binding;
- deterministically ordered PacketManifests;
- deterministically ordered PacketGateManifests;
- a deterministic topological packet order;
- `authority_effect=NONE`.

Each `PacketManifest` MUST explicitly provide:
- `packet_id`, title, status and objective;
- prerequisites;
- required artifacts;
- capability requirements;
- tests;
- acceptance conditions;
- outputs;
- rollback;
- authority required and authority delta;
- gate IDs;
- successor (`next_packet`, nullable only at a terminal packet).

OVC plan-specific detail such as `allowed`, external prerequisites, state transition, inputs, implementation actions and QA requirements is retained when supplied. It is descriptive/contractual packet content; it is not inferred by the compiler.

Missing required packet fields are a hard failure.

## 4. Capability requirements

Each `CapabilityRequirement` MUST state:
- `capability_id`;
- `version_range`;
- `required_tier`;
- `mandatory`;
- reason.

The materialiser validates capability identity only against a supplied DSAI capability registry/read model. It does not select releases or qualify Skills.

Unknown **mandatory** capability IDs fail closed. An unknown optional capability may remain visible in the PacketManifest as a future/non-execution requirement, but MUST NOT enter the existing DSAI PacketGraphSnapshot `required_capabilities` list.

## 5. Gates and authority

Each `PacketGateManifest` MUST explicitly state gate ID/title, gate class, acceptance conditions, authority delta and rollback.

Supported gate classes:
- `AUTO_EXECUTABLE`
- `AUTO_RATIFIABLE`
- `OPERATOR_REQUIRED`
- `OPERATOR_RESERVED`

Auto gates are rejected if their declared or mechanically detectable authority delta contains an operator-reserved action. Packet authority is checked independently: a packet carrying operator-required authority must be attached to an operator gate.

This is a classification guard, not an authority engine. It can reject an unsafe classification; it cannot create or satisfy reserved authority.

## 6. Graph invariants

Materialisation fails on:
- empty or duplicate packet IDs;
- empty or duplicate gate IDs;
- unknown internal prerequisites;
- self-dependency;
- prerequisite cycles;
- unknown gate references;
- a `next_packet` edge not matched by the successor's prerequisite declaration;
- reserved authority hidden under an auto gate.

The compiler computes a deterministic topological order with lexical tie-breaking. Packet and gate list order in the reviewed transcription does not affect deterministic identities.

## 7. Existing DSAI integration

After validation, the materialiser calls the existing `build_packet_graph_snapshot` function from `ovc.development.skills.orchestration`.

It maps only:
- packet identity;
- internal prerequisites;
- mandatory known capability IDs;
- effective operator/auto gate class;
- authority delta;
- packet class.

No parallel PacketGraphSnapshot implementation is permitted. Existing `build_packet_eligibility_record` consumes the emitted graph without adapter semantics.

## 8. Deterministic identity

Logical identities use OVC `canonical_sha256`, which binds canonical JSON logical content to an explicit role. Machine-specific paths, wall-clock timestamps and unordered input iteration MUST NOT affect logical identities.

The MaterialisationReceipt binds:
- ProgrammeManifest identity;
- PlanSourceRef identity and hash;
- source-verification status;
- existing PacketGraphSnapshot identity/hash;
- packet/gate counts;
- topological order;
- validation status.

## 9. Failure policy

All structural ambiguity fails closed. Code/tests do not repair or infer a missing plan decision.

The following are hard failures:
- source mismatch/drift;
- missing mandatory fields;
- graph ambiguity/cycle;
- unknown mandatory capability;
- illegal authority classification.

Callers may correct the reviewed transcription or governing plan through normal OVC governance, then rematerialise. They may not weaken validation to make an invalid plan executable.

## 10. Authority exclusions

This layer grants no:
- Skill TRUSTED promotion;
- Tool Broker or new ORCH activation;
- selector activation/replacement;
- ACTIVE_DISCOVERY, ACTIVE_DEVELOPMENT or ACTIVE_VALIDATION;
- semantic/threshold/model/family/candidate/theory promotion;
- canonical/R2/new immutable release publication;
- provider intake;
- release freeze or active-authority retirement;
- destructive/history-rewrite/force-push authority;
- scope expansion or new instrument/market/clock/side/dependency;
- probability/risk/exposure/E-H/execution/agent-write authority.

Every emitted object has `authority_effect=NONE`.

## 11. Rollback

Rollback is forward-only: revert/supersede the PPM implementation, schemas, fixtures and bindings while preserving the G0 operator decision and historical materialisation evidence. The existing DSAI orchestration/resolution path remains the fallback. No force push or history rewrite is part of rollback.
