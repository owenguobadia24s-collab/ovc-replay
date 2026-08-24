# Persistent Execution Service (PES) Contract v0.1

**Lineage:** prospective successor to CERS persistent-supervisor liveness semantics  
**Scope:** programme-agnostic durable execution/liveness  
**Authority effect:** NONE

## Purpose

PES keeps already-authorized durable work alive across agent, chat, tool-call, runner, and process boundaries. PES is a liveness service, not a semantic owner or authority source.

## Constitutional boundary

1. PES MUST NOT manufacture programme, packet, scientific, execution, writer, merge, VIT, SIQ, GRT, or operator authority.
2. PES MAY advance only work whose governing owner has already made the next action lawful and whose durable prerequisites can be resolved from authoritative state.
3. PES MUST preserve exact packet/PIP/head identities when those identities are authority-bearing. It MUST NOT create payload commits merely to renew liveness or currentness.
4. PES MUST distinguish `WAITING_FOR_PREREQUISITE`, `RUNNABLE`, `PARKED`, `DENIED`, and `COMPLETE`. Missing evidence is never silently promoted to `RUNNABLE`.
5. PES MAY perform bounded reconciliation for asynchronous authoritative receipts. Expiry MUST fail or park closed according to the owning subsystem's law.
6. PES MUST NOT bypass, weaken, reinterpret, or replace VIT ordering, SIQ serialized integration, GRT law, owner authority, or physical-main exclusivity.
7. Physical-main writes remain outside PES. PES may request or observe the existing lawful integration path but cannot become an independent main writer.
8. PES MUST be programme-agnostic. Programme-specific eligibility, semantics, gates, and completion meaning remain owned by the programme or governing subsystem.
9. Durable PES transitions MUST be restartable without conversational liveness and auditable from persistent state.
10. CERS records remain valid historical lineage. New generic liveness work SHOULD use PES terminology; migration does not retroactively rewrite historical CERS evidence.

## VIT qualification liveness adapter

The first active PES adapter is bounded reconciliation for detached exact-head VIT qualification visibility during permanent PR admission.

The adapter:

- observes the detached qualification ledger only;
- does not derive qualification from PR-body lineage;
- does not create or alter authority manifests or dependency frontiers;
- waits only for the exact current candidate head;
- accepts only the existing VIT exact-head/tree validated qualification;
- fails closed with the existing VIT qualification error if the bounded window expires;
- does not mutate the topic branch or manufacture a renewal commit.

This adapter changes liveness only. VIT remains the decision authority for qualification validity and SIQ remains the physical integration gateway.

## CERS succession rule

CERS is retained as historical lineage for the DSAI3V persistent-supervisor programme. Prospectively, its generic restartability, supervision, reconciliation, checkpoint, and durable-liveness concepts are subsumed by PES. Any CERS rule that grants or implies programme-specific semantic ownership does not transfer to PES.
