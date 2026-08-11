# RCN-RN-WP4A — Investigate Translation + Structure Preparation Contract v1

**Programme:** OVC-RC-VNEXT-GREENFIELD-v0.1  
**Plan:** OVC-RCN-RESEARCH-NATIVE-IMPLEMENTATION-PLAN-0.3-RATIFIED  
**Packet:** RCN-RN-WP4A_PREPARATION  
**Authority:** AUTO_EXECUTABLE_PREPARATION_ONLY  
**Source authority:** FIXTURE_ONLY_LOCAL_READ_ONLY  
**Reserved boundary:** RCN-RN-G4 before first real-source presentation

## 1. Purpose

Prepare the Investigate-domain Translation + Structure read contract that may later receive separately-authorised source bindings. This packet exercises only the existing synthetic fixture pack and creates no real-source route, provider intake, activation, promotion, scientific inference or write capability.

## 2. Prepared surface

`GET /api/v1/investigate/snapshot` returns the existing read envelope with schema id `ovc-rcn-investigate-snapshot/v1`. The payload contains four independent planes:

1. **Market context** — optional contextual bars only; never product identity or scientific evidence.
2. **Translation / C1** — exact fixture C1 facts, preserved without reinterpretation.
3. **Structure / C2** — exact fixture C2 axes, computability and FVT; no composite winner or client-derived state.
4. **C2E / transitions** — source-owned when materialized; otherwise explicit typed absence. Missing C2E or transition materialization MUST NOT block lawful C2 presentation and MUST NOT be reconstructed from historical or adjacent data.

The payload also carries preparation-only source-binding candidates. Candidates are declarations, not bindings.

## 3. Binding-candidate rules

Each candidate MUST declare owner, repository namespace, activation state and gate requirement. During WP4A preparation:

- `activation_state = PREPARED_NOT_BOUND`;
- `real_source_presented = false`;
- `authority_effect = NONE`;
- `gate_required = RCN-RN-G4`;
- no filesystem/provider/runtime locator is opened by the public route.

A repository path in the candidate registry characterises the owning namespace only; it is not permission to read or expose that namespace through the console.

## 4. Semantic firewalls

- `AVAILABLE`, `AUTHORISED` and `ACTIVE` remain independent.
- C2 remains usable when C2E is `NOT_MATERIALIZED`.
- C2E current-generation absence is explicit and never replaced by historical C2E.
- Transition absence is explicit and never synthesized from C2 state deltas in the browser or API.
- `confidence_score`, `overall_state` and `winner_axis` are forbidden C2 composites.
- Validation requests are rejected before fixture object/resource resolution.
- React may render and navigate only; scientific classification and authority remain source-owned.
- Market context is optional context only and is never the central acceptance dependency.

## 5. Acceptance

WP4A preparation passes when:

- the aggregate fixture route is deterministic and GET-only;
- fixture banner remains `SYNTHETIC_FIXTURE / NON_EVIDENTIARY / authority_effect=NONE`;
- C1 and C2 are preserved exactly from the fixture source;
- C2E and transition gaps remain typed and fail-honest;
- every proposed source binding remains `PREPARED_NOT_BOUND`;
- Validation is denied before resource reads;
- the route registry and OpenAPI snapshot remain read-only;
- full Research Console CI passes.

## 6. Non-effect and rollback

This packet grants no real-source presentation/intake, selector/model/family/ObjectPack/event/C3 activation or promotion, Validation, publication, console/governance writes, probability, risk, exposure, trading or execution authority.

Rollback is removal of the WP4A preparation route/contracts/fixtures/registry and restoration of the G3V-merged fixture-only baseline. RCN-RN-G4 remains required regardless of rollback.