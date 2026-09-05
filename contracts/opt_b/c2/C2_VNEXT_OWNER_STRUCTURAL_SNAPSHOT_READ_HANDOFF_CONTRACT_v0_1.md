# C2 vNext Owner Structural Snapshot Read Handoff Contract v0.1

**Contract ID:** `C2.VNEXT.OWNER.STRUCTURAL.SNAPSHOT.READ.HANDOFF.v0.1`  
**Owner:** `OPT-B.C2.vNext`  
**Current owner authority:** `AUTH.OPT-B.C2.vNext.ACTIVE.RUNTIME.v0.1`  
**Current owner package:** `C2AR.INTEGRATED.SHADOW.PACKAGE.v1`  
**Operator instruction:** `OVC APPROVE read-only C2 owner handoff`  
**Authority effect:** `READ_ONLY_CURRENT_OWNER_STRUCTURAL_SNAPSHOT_HANDOFF_ONLY`

## 1. Purpose

This contract materialises the missing public current-owner read surface required by downstream governed research. It exposes exact current C2 vNext structural records and their chronology/provenance without allowing a consumer to reconstruct private owner state, select hidden alternatives, change C2 semantics, or create new source authority.

The handoff exists so Research Operations can execute long-population, separately authorised cross-asset, and separately authorised multiclock studies while specialised research remains portable rather than permanently fused into the C2 owner.

## 2. Owner generation

The handoff is bound to the exact current owner generation declared by `C2_OWNER_STRUCTURAL_SNAPSHOT_GENERATION_v0_1.json`. That generation binds:

- `AUTH.OPT-B.C2.vNext.ACTIVE.RUNTIME.v0.1`;
- `C2AR.INTEGRATED.SHADOW.PACKAGE.v1` and its package SHA-256;
- the exact nine active C2 vNext component implementations;
- the exact public component schema identities used by the read surface;
- the current active market envelope only.

A package, schema, implementation, owner-authority, or active-envelope drift requires a new owner generation. Consumers may not silently continue across generation drift.

## 3. Read-only owner API

`src/ovc/opt_b/c2_vnext/owner_read_surface.py` is the public read-derive boundary.

It may:

1. accept already-authorised, source-bound C1/OPT-A rows for the current C2 market envelope;
2. invoke the existing C2 vNext owner materialisation machinery without changing its algorithms;
3. return deterministic structural snapshots composed only from exact owner-produced records and exact owner joins;
4. expose source, chronology, continuity, missingness and generation identities required for downstream admissibility.

It may not:

- write or mutate active C2 state;
- select or replace a C2 selector, threshold, formula, clock, lattice, release or parameter pack;
- inspect private consumer-inaccessible fields outside the declared public surface;
- substitute historical C2 v2 state for current owner truth;
- infer C2E, C2P, C2.5, C3, outcome, probability, risk, exposure, trading or execution state;
- grant a new provider, instrument, market, side, clock or research role.

Runtime artifact writing, if a Research Operations stage chooses to persist returned snapshots, belongs to that stage's separate output authority and is not an owner-state write.

## 4. Current source envelope

This v0.1 handoff is restricted to the already-effective C2 vNext envelope:

- instrument: `GBPUSD`;
- sides: `BID`, `ASK`;
- local clock: `15M`;
- parent clock: `2H_A_L`;
- research roles already present on the active stack: `DISCOVERY`, `DEVELOPMENT`;
- Validation: `LOCKED_UNCONSUMED`.

Provider and source-object identities are provenance fields, not grants. Every invocation must name an already-authorised source authority reference and exact source-release/object identities.

## 5. Chronology

The owner observation contract remains binding:

- `interval_start` and `interval_end` are source/effective chronology;
- `effective_time` for the snapshot is `interval_end`;
- `first_valid_time` is carried separately from the owner observation record;
- under the current observation contract `first_valid_time == interval_end`, but the roles remain distinct and downstream code may not collapse them into one semantic field;
- no component whose first-valid time is later than the snapshot first-valid time may be joined.

## 6. Warm-up, gaps and discontinuities

Warm-up and break conditions remain first-class owner evidence. The public surface carries the exact observation continuity/projection facts and exact horizon/component status/reason codes.

No missing or unavailable component may be converted to neutral, zero, unchanged, false, nearest, best, dominant or fallback state. `WARM_UP_INSUFFICIENT`, closure, gap/reset, partition boundary, unknown break and component-specific non-computability remain distinguishable.

## 7. Public field classes

The surface exposes:

- owner/generation identity;
- source authority and release/object provenance;
- instrument, side and exact clock identities;
- observation identity and interval/FVT chronology;
- exact observation continuity and projection eligibility;
- exact owner records referenced by the structural bundle: horizon memberships, levels, containers, relation sets, four-axis formula profiles and parent context;
- transition and computability slots only when exact owner records are present; otherwise explicit typed absence;
- exact component schema/code binding references.

Embedded owner records remain owner-typed records. A downstream adapter may consume only fields admitted by its own frozen protocol and by the corresponding owner schema. The handoff itself does not flatten the owner records into a new state ontology.

## 8. Determinism and identity

Snapshots are canonical JSON objects with a content-derived `snapshot_id`. Ordering is deterministic. Duplicate owner IDs with different bytes fail closed. References that cannot be resolved exactly fail closed.

The public API must restore any temporary owner-scope configuration after each invocation so one population cannot leak scope into another.

## 9. Consumer authority

The grant is read-only current-owner consumption for governed Research Operations. It does not by itself activate RRSCG, SPTO, C2P, C2.5, C3 or any other consumer programme.

Consumer-specific adapters, scientific claims, source/population admissions and active research roles remain separately governed.

## 10. Explicit non-grants

This handoff grants no:

- new provider, instrument, market, side or clock;
- selector activation/replacement;
- new C2 semantic, family, candidate, model or theory authority;
- C2E boundary-pack replacement;
- C2P/C2.5/C3 activation;
- Validation consumption;
- canonical or R2 publication;
- probability, risk, exposure, trading or execution authority;
- agent-write authority.

## 11. Rollback

Forward-only. A later owner packet may supersede or disable this read surface while preserving the operator decision, exact generation, all emitted research artifacts and Git history. No force-push or historical rewrite is permitted.
