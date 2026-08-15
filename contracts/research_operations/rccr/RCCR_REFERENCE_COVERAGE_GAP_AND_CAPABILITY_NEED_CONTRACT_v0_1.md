# RCCR Reference Coverage, Gap and Capability-Need Contract v0.1

Status: IMPLEMENTED INACTIVE / NON-AUTHORITATIVE SYNTHESIS; INDEPENDENT ALGORITHMIC REVIEW REQUIRED BEFORE G4.

## Requirement-level coverage

RCCR evaluates every frozen requirement individually. It emits a coverage vector and answerability state; no scalar coverage score, ranking or winner is permitted. Missing requirement evidence becomes explicit `NOT_EVALUABLE / UNRESOLVED_GAP`; it is never silently dropped or sampled.

## Diagnostic precedence

The reference engine uses this fail-closed order:

1. protocol invalid / out of scope;
2. protocol exclusion;
3. method-information entanglement (remain `UNRESOLVED_GAP`);
4. method / capacity / review;
5. denominator;
6. owner semantics;
7. implementation / authority;
8. data;
9. information absence last.

`INFORMATION_GAP` is lawful only when smaller explanations have been explicitly exhausted. Otherwise the result remains `UNRESOLVED_GAP`. `METHOD_INFORMATION_ENTANGLED` is never forced into either METHOD_GAP or INFORMATION_GAP.

## Counterfactual sufficiency

Every information-gap claim records whether method, capacity, review, denominator, owner-semantics, implementation, authority and data explanations were checked. Capability-need assessment is eligible only from an exhausted information gap and must remain falsifiable, owner-bound and minimal.

## Capability-need non-authority

Before evidentiary EC1 and owner-governed scientific review, the reference engine may produce `EVIDENCE_REQUIRED`, `NOT_REQUIRED`, `NEED_CONTRADICTED` or `UNRESOLVED`. It may not use pre-evidentiary RCCR machinery to self-promote `NEED_SUPPORTED`, activate a capability or request authority. `authority_requested=NONE` and `authority_effect=NONE` are mandatory.

## Independent review interlock

Every requirement result carries an explicit decision trace including input result, flags, precedence table, selected gap and reason. RCCRI-G4-ALG must independently inspect decision-path logic, diagnostic precedence, METHOD_INFORMATION_ENTANGLED handling, INFORMATION_GAP transition and CapabilityNeedAssessment eligibility. The implementation author may not self-review this gate.

## Replay

The reference path is deterministic and order invariant. Replay consumes the complete declared requirement set. There is no top-N, winner, hidden sampling, fallback inference from downstream outcomes, or Validation access.
