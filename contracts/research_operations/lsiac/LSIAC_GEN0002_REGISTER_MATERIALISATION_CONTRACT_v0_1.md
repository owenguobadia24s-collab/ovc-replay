# OVC LSIAC GEN0002 Register Materialisation Contract v0.1

**Programme:** `OVC-LSIAC-v0.1`  
**Packet:** `LSIAC-GEN0002-LSIR-REGISTER-MATERIALISATION`  
**Source Pass2 merge:** `0c4fb692086854cd341467de7e73baae249b2910`  
**Source Pass2 virtual view:** `58b364fbf7b8ce160877fb8bba641cb853ea1b29b5af9c4a4b1a5294648749d8`  
**Authority effect:** `NONE_REGISTER_MATERIALISATION_ONLY`

## Purpose

Materialise the six post-Pass2 register surfaces required by the ratified LSIAC sequence without re-adjudicating any scientific subject and without executing any downstream change. The source of truth is the effective GEN0002 Pass2 adjudication view and its 431 frozen scientific accession decisions.

## Bound inputs

The materialiser SHALL bind the effective Pass2 virtual-view identity, the operator Pass2 authority decision `7130e987c4ba3900eff0abfc43d4989d9899393ef151e2a975dd5b5d04377c84`, the unchanged GEN0002 protocol binding `15e449ffe15ded1d6419533257515ab9686122a1b5c73f7c82c49cea6e273d4f`, and the effective Pass1 virtual view. Identity drift fails closed.

## Register projections

`LSIR` contains only Pass2 decisions carrying at least one non-`NONE` inheritance role. Every Pass2 decision remains present in a non-authoritative decision index so a zero-entry LSIR cannot hide adjudicated subjects.

`NegativeKnowledgeRegister` contains only Pass2 decisions explicitly assigned `NEGATIVE_KNOWLEDGE`. `NEGATIVE_SUPPORTED` source disposition alone is not promoted into the register; such subjects remain listed as deferred negative subjects when no inheritance role was admitted.

`SupersessionRegister` contains only supersession edges already present in effective Pass2 decisions. No supersession may be inferred from title similarity, lineage, chronology, replacement history or a no-forward outcome.

`DestinationBindingRegister` contains only non-empty Pass2 destination binding sets. Empty sets remain counted but do not invent an owner or consumer destination.

`ArchitectureEffectRegister` materialises the Pass2 architecture-effect set for every adjudicated subject. These records are declarative metadata only. They do not execute owner, contract, semantic, selector, Validation, publication or runtime changes.

`ArchitectureGapRegister` may create a `REPRODUCIBILITY_BLOCKER` entry only from explicit Pass2 counterevidence `source_binding_debt`. It may not infer scientific-destination, cross-architecture or owner-export gaps from absence of a forward role.

## Scientific and authority invariants

This packet SHALL NOT alter Pass2 decision bytes or decision semantics; create a new scientific accession decision; upgrade a claim-strength cap; assign or remove an inheritance role; create `RETAIN_FORWARD`; resolve source-binding debt; create a destination; create a supersession edge; or execute an architecture effect.

`LSIAC-SCIENCE-RESUME`, downstream architecture/owner changes, selector/model/family/theory or semantic activation, C2E/C2P/C2.5/C3 activation, ESL admission, Validation consumption, canonical/R2 publication, new immutable release identity, real-provider intake, probability/risk/exposure/E-H/trading/execution and agent-write authority remain denied.

## Acceptance

The bundle SHALL deterministically materialise all six required register kinds, preserve complete 431-decision traceability, emit zero new scientific decisions and zero downstream executions, preserve the fail-closed Pass2 result, and be reproducible from the exact source Pass2 view.

## Successor

After lawful integration, the next packet is `LSIAC-GEN0002-ARCHITECTURE-RECONCILIATION`. That packet may reconcile register evidence only; it cannot execute downstream changes. `LSIAC-SCIENCE-RESUME` remains a separate operator-required gate.

## Rollback

Rollback is forward-only. Preserve the effective Pass2 court record and all register evidence. Correct deterministic projection defects in a successor packet; never rewrite the Pass2 adjudication or broaden authority to make a register non-empty.
