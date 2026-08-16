# OVC Shared Systems Stage-0 Bootstrap Contract v0.1

Programme: `OVC-SHARED-SYSTEMS-v0.1`  
Plan: `OVC-SHARED-SYSTEMS-CONFORMANCE-IMPLEMENTATION-PLAN-0.2-R1`  
Packet / gate: `SHSI-WP0 / SHSI-G0B`  
Authority: `INACTIVE_REFERENCE / SHADOW_ONLY`; Stage-0 authority effect `NONE`.

## Purpose

Stage 0 proves that Shared Systems can exist lawfully and reproducibly before any steady-state shared runtime is constructed. It consumes the already-ratified G0A AuthorityEnvelope and the already-current GRT `SharedServiceBinding`; it MUST NOT create a second owner binding.

## B0-B6 dependency constitution

The normative bootstrap order is:

`B0 immutable primitives -> B1 bootstrap validation manifest -> B2 exact design/plan bundle validation -> B3 GRT repository classification/binding contract -> B4 exact SharedServiceBinding -> B5 shared registry/resolution runtime -> B6 consumer migration/adoption`.

WP0 materialises and proves B0-B4. B5/B6 are represented only as downstream reachability nodes. No B0-B4 operation may import or invoke steady-state Shared Systems registry/resolution/runtime, DSAI full execution/security runtime, or a Shared Systems resolver to create/choose the owner it is proving.

## Identity and owner rules

- Governing design: `OVC-SHARED-SYSTEMS-DESIGN-SPEC-0.1-R1`, SHA-256 `344a74d78e0d04650bb55d62a4871dbb2b23f6ae80324222d1034ebea1c3556a`.
- Governing plan: `OVC-SHARED-SYSTEMS-CONFORMANCE-IMPLEMENTATION-PLAN-0.2-R1`, SHA-256 `7a31e08fb5c8e556e81540bbb1d0e63d18c60029335615d78ca193a24f009659`.
- G0A decision: `SHSI-G0A-RATIFICATION-v0.2-R1`.
- Binding: `GRT.SHARED_SERVICE_BINDING.OVC_SHARED_SYSTEMS.v0.1`.
- Binding canonical hash: `46e4d03f56c1dd27fbdc0828c30b1910fc4b7510ec56bdb7b089edc1e2780945`.
- Exactly one owner is permitted: `OVC-SHARED-SYSTEMS-v0.1`.
- Service state at Stage 0 remains `INACTIVE_NOT_IMPLEMENTED` / `INACTIVE_BOOTSTRAP`.

The GRT binding registry canonical hash is SHA-256 over canonical JSON after omission of the `canonical_hash` field. Conflicts, multiple matches, altered owner identity, non-resolved binding state, consumer activation, or changed authority effect fail closed.

## Canonical bootstrap serialization

Stage-0 logical proof serialization is UTF-8 JSON with sorted object keys, no insignificant whitespace, `ensure_ascii=false`, and `allow_nan=false`. The same payload must produce identical canonical bytes and SHA-256 after a clean JSON decode/re-encode round trip.

## Stage-1 barrier

`SHSI-WP1` is not READY until `SHSI-G0B` is `COMPLETED` on lawful main. Passing local tests, branch-only records, an ephemeral synthetic B5/B6 fixture, or a chat statement cannot satisfy the barrier.

## Rollback

Before merge, close/preserve the branch and evidence. After merge, correct forward with a superseding generation. Never rewrite the G0A decision, GRT owner binding, design identity, plan identity, or baseline evidence.
