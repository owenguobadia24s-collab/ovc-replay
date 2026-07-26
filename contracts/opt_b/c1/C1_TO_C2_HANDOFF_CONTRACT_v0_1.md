# C1-to-C2 Handoff Contract v0.1

## Authority

This contract defines the exact read interface that a future OPT-B.C2 package may validate against. It does **not** authorise C2 consumption, C2 implementation, C2 activation, Validation access, semantic classification, probability, exposure, trading or execution.

## Admissible parent

C2 may eventually consume only a C1 role selector explicitly authorised by a separate C2 gate. At B1-G5, the Discovery and Development C1 releases are selected as `SHADOW`; `c2_consumption` remains `DENIED_PENDING_SEPARATE_HANDOFF_REVIEW`.

## Required C1 fields

Every consumed C1 record must expose:

- exact `c1_release_id`, `record_id`, `manifest_id` and manifest SHA-256;
- exact parent OPT-A release, manifest and source-bar identities;
- `clock` in `15M` or `2H_A_L` and `price_side` in `BID` or `ASK`;
- all 18 measurements with exact formula-registry versions;
- explicit null, quality and non-computability reasons;
- `first_valid_time` no earlier than every required parent input;
- deterministic identity independent of runtime, machine and local path.

## One-way dependency law

C2 may name exact C1 fields it reads. It may not request bare “C1 features,” alter C1 history, repair a null, convert a reason code to zero or `NEUTRAL`, read future outcomes, or write back into C1 releases.

## Role and clock law

A future C2 release must declare the same role, clock and side as its C1 parents unless a separately frozen cross-clock contract exists. Mixed-role, mixed-release or unapproved cross-side parentage is rejected.

## Shadow boundary

B1-G5 proves that the published C1 releases are selectable and interface-complete. Shadow selection permits inspection and comparison only. It grants no downstream read authority. C2 remains `DESIGN_AND_FIXTURES_ONLY` until its own scope, contract and parent-release gates pass.

## Rollback

Rollback atomically returns the Discovery and Development C1 selectors to `NONE`. Published releases, manifests, gate packets and historical selector decisions remain immutable and auditable. Legacy OPT-B and historical OPT-A v1 are prohibited rollback targets.
