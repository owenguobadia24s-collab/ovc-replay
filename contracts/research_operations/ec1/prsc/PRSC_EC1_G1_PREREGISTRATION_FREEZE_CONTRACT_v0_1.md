# PRSC EC1-G1 Preregistration Freeze Contract v0.1

## Scope
PRSCI-WP9 constructs the exact preregistration machinery for the EC1-G1 PRSC method constitution. Build-ahead work may construct and test deterministic freeze/readiness machinery, but it MUST NOT mark a protocol `FROZEN`, satisfy `PRSCI-G-PREREG`, or create real-source PRSC authority before `PRSCI-G8-ALG=PASS` and the operator gate.

## Pre-E1 information firewall
A confirmatory EC1-G1 `PRSCProtocolGeneration` MUST be constructed only from information admissible before inspection of E1 decision-bearing candidate results. Any recorded E1 decision-bearing inspection before `PRSCI-G-PREREG=PASS` makes the generation ineligible for confirmatory preregistration and requires a successor/exploratory generation.

## Frozen constitution
The preregistration bundle binds exact method-pack references, the exact scientific-hypothesis-family registry, candidate-class claim templates, fatality/disposition rules, reviewer constitution, source namespaces, and the protocol generation identity. Missing or unresolved bindings fail closed.

## Synthetic vertical slice
WP9 must support a synthetic `CandidateProposal -> PRSC -> P1CandidateReviewCard/Q08` path without real E1 reads, CandidateFreeze, Development/Validation access, publication, probability, risk, exposure or execution authority.

## Operator boundary
`PRSCI-G-PREREG` is OPERATOR_REQUIRED. A readiness receipt is evidence for that decision only. PASS may freeze the exact protocol generation; it does not authorize real PRSC read/append and does not lift F0-A HOLD.

## Preserved constraints
F0-A remains `HOLD`; Validation remains `LOCKED_UNCONSUMED`; CandidateFreeze remains `NONE`; real-source PRSC remains denied until `PRSCI-G-EC1-CHALLENGE`.