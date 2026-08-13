# OVC DSAI Plan/Packet Materialisation — Approved Scope v0.1

Status: OPERATOR APPROVED — DSAI-PPM-G0 PASS  
Programme: OVC-DSAI-PPM-v0.1  
Governing decision: DSAI-PPM-G0  
Approval time: 2026-08-13T07:36:00+01:00  
Approval-observed main: 8ce1eb5bb3749074b1d5c40f7ce11f974b6c2d30  
Implementation preflight baseline: bdcf2d96b646b6f5c1e958029bfaf4c782c22d9c

## Purpose

Add one bounded deterministic layer between ratified OVC implementation-plan prose and the existing DSAI packet/orchestration machinery. The layer materialises an operator-reviewed transcription into exact PlanSourceRef, ProgrammeManifest, PacketManifest, CapabilityRequirement, PacketGateManifest, existing DSAI PacketGraphSnapshot, and MaterialisationReceipt records.

## Required behaviour

- Bind every materialisation to exact plan identity, version, source reference and SHA-256.
- Preserve normal OVC work-packet vocabulary: objective, prerequisites/predecessor, allowed authority, state transition, inputs, required artifacts/implementation actions, capability requirements, tests/QA, acceptance, outputs, gate, authority required/delta, rollback and next packet.
- Canonicalise deterministic identities and ordering.
- Reject missing mandatory packet fields, duplicate packet/gate identities, unknown internal prerequisites, prerequisite cycles, inconsistent successor edges and unknown gate references.
- Reject unknown mandatory capability identities while leaving release/Skill selection to the existing DSAI resolution layer.
- Reject auto-ratifiable classification when the packet or gate contains operator-reserved authority.
- Detect source-hash mismatch and post-materialisation governing-source drift.
- Emit a PacketGraphSnapshot directly consumable by existing DSAI packet eligibility/orchestration functions.
- Provide representative DSAI, C2P and OPT-B ESL plan-style fixtures plus negative/adversarial tests.
- Provide deterministic schemas, QA evidence, decision records, machine-readable programme state and rollback.

## Explicit non-scope

This layer is not a DOCX interpreter and does not infer missing plan semantics. It does not grant TRUSTED Skill status, Tool Broker or new ORCH authority, selector/model/family/semantic activation, Discovery/Development/Validation authority, publication, provider intake, probability/risk/exposure/E-H/execution authority, destructive action or history rewrite.

## Packet sequence

DSAI-PPM-WP0 records the operator admission decision and source/authority boundary. DSAI-PPM-WP1 implements contracts, schemas, fixtures, deterministic materialisation, DSAI graph integration, tests and QA. DSAI-PPM-G1 is auto-ratifiable only when all tests pass, QA recommends PASS, no unresolved blocker remains and authority delta is NONE.

## Baseline reconciliation

The operator approval was issued while main was `8ce1eb5bb3749074b1d5c40f7ce11f974b6c2d30`. Before permanent mutation, main advanced linearly to `bdcf2d96b646b6f5c1e958029bfaf4c782c22d9c` through the DSAI2 terminal closeout. The PPM branch was fast-forwarded without force to that lawful latest main before implementation. This baseline movement grants no new authority and does not alter the approved PPM scope.

## Rollback

Forward-revert or supersede the PPM implementation, schemas, fixtures and bindings while preserving the G0 decision and historical evidence. Existing DSAI resolver/orchestrator behaviour remains the fallback; no force-push or history rewrite is permitted.
