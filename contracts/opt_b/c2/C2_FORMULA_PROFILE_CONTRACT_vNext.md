# C2 Formula Profile Contract vNext r1

Programme: `OVC-C2-ANATOMY-REDESIGN-v0.2`  
Packet: `C2AR-WP6-IMPLEMENTATION`  
Authority: `CEAR-G6.OPERATOR.PASS.20260804T225200+0100`  
Maturity: `SHADOW_FROZEN`

## Purpose

Formula profiles expose deterministic, read-only axis evidence from the frozen observation, horizon, level, container and relation interfaces. They neither choose trading meaning nor activate a selector, threshold, parameter, scale, semantic label, release or downstream consumer.

## Common contract

Every profile output contains its immutable profile ID, axis, input IDs, causal as-of time, computability, reason codes, raw facts, `active=false`, `canonical=false`, an empty numeric-threshold list and authority `SHADOW_FROZEN_READ_ONLY`. Output identity is a SHA-256 over canonical content.

Profiles fail closed when an input is future-dated, internally inconsistent, incomplete for its declared scope or contains prohibited future/outcome, probability, risk, exposure, trading or execution fields. Missing evidence becomes explicit per-profile `NOT_COMPUTABLE`; another profile, object, horizon or scale is never substituted.

## LOCATION — raw geometry

`C2.FORMULA.LOCATION.RAW_GEOMETRY.v1` consumes complete scoped relation sets and raw level/container relations. It exposes topology, signed and absolute distance, boundary distances, relation IDs and explicit exclusions. It does not select a best, nearest, dominant or fallback object.

## MOTION — typed-horizon delta

`C2.FORMULA.MOTION.TYPED_HORIZON_DELTA.v1` consumes one named horizon membership, raw price delta and same-object relation deltas. It exposes the horizon ID, membership status, price delta, signed-distance delta and absolute-distance change. It does not infer trend strength, direction probability, a universal horizon or a forward outcome.

## ORGANISATION — container graph

`C2.FORMULA.ORGANISATION.CONTAINER_GRAPH.v1` consumes complete container and optional swing graphs. It exposes container kind, structural depth, lower/upper/width/centre geometry and raw graph edges. It does not choose a winning container, infer parentage from width or emit regime/episode meaning.

## INTERACTION — raw transition input

`C2.FORMULA.INTERACTION.RAW_TRANSITION_INPUT.v1` consumes raw relation deltas, fixed-object crossing evidence and reference-change records. It exposes topology before/after, distance changes, path-order availability, crossing status and identity changes. `APPROACHING`, `TESTING`, `REJECTING`, `ACCEPTING`, event and episode outputs are prohibited.

## QUALITY — per-component computability

`C2.FORMULA.QUALITY.PER_COMPONENT_COMPUTABILITY.v1` consumes named component quality records. It preserves each component's status, reason codes, lineage and censorship/ambiguity/conflict flags. It never collapses components into one global degraded, neutral or probabilistic state.

## Complete bundle

A formula bundle contains exactly LOCATION, MOTION, ORGANISATION, INTERACTION and QUALITY in registry order. Each axis remains independently computable. Bundle status is `COMPLETE`, `PARTIAL_NOT_COMPUTABLE` or `NOT_COMPUTABLE`; this status carries no semantic market meaning.

## Freeze and supersession

The profiles consume `C2AR.INTEGRATED.SHADOW.FREEZE.v1`. The five source revision ledgers remain immutable historical records; the integrated freeze transitions their use to `SHADOW_FROZEN` through a separate hash-pinned record. Any profile or interface change requires a new version and supersession record.

## Explicit non-authority

No active C2 mutation, selector activation/replacement, numeric threshold/parameter/scale selection, semantic or detector promotion, parent resolver, denominator policy, rule/theory promotion, provider intake, canonical/R2 publication, Validation consumption, release activation, C2E/C2.5/C3, probability, risk, exposure, trading, execution or agent-write authority.

## Rollback

Rebuild derived profile outputs from frozen inputs. Supersede contracts or implementations only through a new version and authorised decision. Preserve all prior hashes, decisions and freeze records.
