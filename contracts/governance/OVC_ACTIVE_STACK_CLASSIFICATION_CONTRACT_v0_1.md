# OVC Active Stack Classification Contract v0.1

Programme: `OVC-ACTIVE-STACK-RECLASSIFICATION-v0.1`
Authority: operator-approved reclassification, effective only when the bounded packet is merged to `main`.

## 1. Current-authority precedence

For new evidence collection, `registries/governance/active_stack/CURRENT_ACTIVE_STACK_POINTER.json` is the governing stack-classification source after this packet merges. Earlier selector, programme-terminal and activation records remain immutable historical evidence but are superseded where this contract explicitly says so.

Historical replay tooling may read superseded records only under explicit historical-lineage/reproducibility scope. It may not use them as current parents for new evidence.

## 2. Classification vocabulary

`ACTIVE`: authoritative producer/transform for new evidence inside the declared market envelope.

`ACTIVE_FOUNDATION`: operational infrastructure/enrichment usable by the active stack but forbidden from redefining upstream structural identity or silently expanding scientific authority.

`SHADOW`: implemented deterministic research surface that may produce evidence but has no authority to redefine active truth, choose canonical methods, promote families/semantics or publish.

`NON_EVALUABLE`: forward implementation/evidence surface is insufficient for meaningful operational evaluation. Design-only or historical names do not qualify as SHADOW.

`LEGACY_INACTIVE`: preserved historical implementation/evidence with current runtime-parent and selector eligibility denied for new evidence.

`LOCKED`: implemented or reserved surface whose consumption is explicitly prohibited under current authority.

## 3. Active spine

The only active structural spine for new evidence is:

`OPT-A -> C1 v2 -> C2 vNext core -> C2E v0.2`

C2 vNext core is exactly the frozen nine-component subset of `C2AR.INTEGRATED.SHADOW.PACKAGE.v1`: Observation, Horizon, Level, Container, Relation, Formula, Transition, Parent Context and Computability.

C2 vNext `FUNCTIONAL_DISCOVERY` and `CANDIDATE_DISPOSITIONS` remain SHADOW.

## 4. Legacy C2 supersession

The historical `registries/opt_b/c2/C2_ACTIVE_SELECTORS.yaml` transaction and `registries/authority/C2_ACTIVE_DISCOVERY_AUTHORITY.yaml` are preserved for lineage. Their current authority effect is superseded for new evidence. `OPT-B.C2.v2` is `LEGACY_INACTIVE` and cannot be a new-evidence parent, selector source or rollback target without a later explicit operator decision.

## 5. C2E active-engine rule

C2E remains active under the exact currently operator-selected boundary pack. Population identity, run token and date-window identity are not activation identities for new evidence inside the existing market envelope.

A governed Discovery/Development C2 vNext population may run through the active C2E engine without a new C2E activation decision when:

- instrument is GBPUSD;
- side is BID or ASK;
- clock is 15M or 2H_A_L;
- upstream C2 vNext authority resolves ACTIVE;
- the currently active boundary pack is unchanged;
- source/provider authority already exists;
- Validation is not consumed.

Any boundary-pack selection/replacement, boundary semantic change, threshold/parameter promotion, new instrument/side/clock, Validation access or provider intake requiring new approval remains operator-reserved.

## 6. OccurrenceContext and Research Operations

OccurrenceContext is `ACTIVE_FOUNDATION` only as non-structural enrichment. `REPRESENTATION_INPUT` remains denied; context may not mutate C2/C2E identity or history.

Research Operations is `ACTIVE_FOUNDATION` within its already-approved read-only and bounded append-only authority. This contract grants no new write, publication or scientific authority and does not auto-pass any evidence-sufficiency gate.

## 7. Validation and exposure firewall

Validation remains `LOCKED_UNCONSUMED`. Probability, risk, exposure, trading, execution and agent-write authority remain NONE.

## 8. Resolver behavior

Any new evidence orchestration added after this packet must resolve the current stack pointer before selecting a producer/consumer path and must fail closed if:

- a requested active producer is classified LEGACY_INACTIVE, NON_EVALUABLE or LOCKED;
- market envelope fields exceed the approved scope;
- a SHADOW output is presented as active/canonical truth;
- an authority overlay and current pointer disagree.

## 9. Rollback

Rollback is additive supersession only. Historical evidence and prior selector decisions remain preserved. No deletion, force-push or history rewrite is permitted.
