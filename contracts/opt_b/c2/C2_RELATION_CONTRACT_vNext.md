# C2 Raw Relation, Topology and Fixed-Object Transition Contract vNext r1

Programme: `OVC-C2-ANATOMY-REDESIGN-v0.2`  
Packet: `C2AR-WP5`  
Gate: `CEAR-G5`  
Normative maturity at gate: `NORMATIVE_BOUNDARY`  
Probe adapters, proximity scales and ordered-path payloads: `SHADOW_EXPERIMENT`

## Purpose

Relations record raw price-to-object geometry before interpretive labels. They preserve subject probe, object identity, signed and absolute distances, topology, equality precision, normalization provenance, crossing evidence and scoped completeness. They do not label approach, test, rejection, acceptance, interaction or market meaning.

## Accepted Part 5 decisions

| ID | Frozen rule |
|---|---|
| P5-D1 | Raw facts precede interpretation. |
| P5-D2 | Every relation names an explicit point, body-span, bar-span or ordered-path probe. |
| P5-D3 | Preserve signed and absolute distance separately. |
| P5-D4 | Signed distance is `subject − object`. |
| P5-D5 | Equality is a source-precision fact distinct from proximity. |
| P5-D6 | Every normalized distance names an explicit scale, value, policy, source and first-valid time. |
| P5-D7 | Missing or unavailable normalization has no fallback. |
| P5-D8 | Point/span topology is separate from path crossing. |
| P5-D9 | Crossing requires the same immutable object identity across chronological evidence. |
| P5-D10 | A reference-identity change is not a crossing. |
| P5-D11 | OHLC span proves only interval coverage; it cannot establish intrabar path order. |
| P5-D12 | Path crossing requires ordered M1 or tick evidence. |
| P5-D13 | Container topology distinguishes below, lower boundary, inside, upper boundary and above. |
| P5-D14 | Bar span and body span are separate probes and relation records. |
| P5-D15 | Both level and container geometry are supported without collapsing object families. |
| P5-D16 | Completeness is scoped to the explicitly declared candidate object population. |
| P5-D17 | Hidden nearest, best, dominant or fallback object selection is prohibited. |
| P5-D18 | An exclusion is local to one scoped relation set and must carry a reason. |
| P5-D19 | Causal-as-of and retrospective-audit outputs are distinct modes. |
| P5-D20 | `APPROACHING`, `TESTING`, `REJECTING` and `ACCEPTING` are not base relation states. |

## Accepted working dispositions

- **P5-Q1:** base probes are OPEN, CLOSE, BODY_SPAN and BAR_SPAN; ordered path is separately sourced.
- **P5-Q2:** equality uses instrument/source precision and is never inferred from a proximity threshold.
- **P5-Q3:** multiple named proximity/normalization scales may coexist; none is canonical at CEAR-G5.
- **P5-Q4:** raw side and distance changes are recorded before any later hysteresis.
- **P5-Q5:** crossing evidence modes are `OHLC_SPAN`, `M1_PATH` and `TICK_PATH`; only ordered modes may assert directional crossing.
- **P5-Q6:** relation scopes remain separate for local levels, parent levels, local measurement containers, local structural containers, parent measurement containers and parent structural containers.
- **P5-Q7:** decreasing absolute distance remains a raw delta and is not labelled approaching.
- **P5-Q8:** parent levels, measurement containers and structural envelopes remain independent relation populations.

## Probes

`POINT` names one exact observed value. `BODY_SPAN` records min(open, close) to max(open, close). `BAR_SPAN` records low to high. `ORDERED_PATH` references chronologically ordered M1 or tick values. The four probe forms never substitute for one another.

## Level facts

Point-to-level relations expose object value, signed distance, absolute distance, sign convention, source-precision equality and `BELOW`, `EQUAL` or `ABOVE` topology. Span-to-level topology is `ENTIRELY_BELOW`, `TOUCHES`, `STRADDLES` or `ENTIRELY_ABOVE`; `STRADDLES` is not a path-crossing claim.

## Container facts

Point topology is `BELOW`, `ON_LOWER_BOUNDARY`, `INSIDE`, `ON_UPPER_BOUNDARY` or `ABOVE`. Span topology preserves lower/upper touch, lower/upper crossing, full coverage, inside and disjoint states. It never asserts an ordered path.

## Normalization

A `NormalizationScale` is immutable, positive, source-linked and first-valid. Multiple named scales may be attached simultaneously. No scale is active or canonical during this programme. If a requested scale is unavailable or not first-valid, the normalized fact is absent or fails closed; another scale is never substituted.

## Fixed-object crossing

Directional crossing is evaluated only against one unchanged object ID and value over chronological evidence. `OHLC_SPAN` may report `SPAN_STRADDLES_PATH_ORDER_UNKNOWN`; it cannot report `CROSS_UP` or `CROSS_DOWN`. Ordered M1/tick paths may report directional crossing, touch or no-cross. A changed reference emits a separate `REFERENCE_IDENTITY_CHANGE_ONLY` record with `is_crossing=false`.

## Temporal delta

Relation deltas require the same object identity and preserve signed-distance delta, absolute-distance delta, topology before/after and raw increase/decrease/unchanged. Semantic fields for approach or test remain null.

## Scoped relation sets

A relation set declares one subject, scope, mode and complete candidate object IDs. Every candidate appears exactly once as a relation or explicit exclusion. The record contains no selected or fallback object. Exclusion cannot delete the object globally or change another scope.

## Causal and retrospective modes

`CAUSAL_AS_OF` requires every object and scale to be first-valid by the probe time and prohibits future/outcome fields. `RETROSPECTIVE_AUDIT` is separately marked and may not enter causal C2 state construction.

## Legacy crosswalk

Historical raw topology may map to vNext relation IDs. Legacy labels such as approach/test/reject/accept are preserved as historical metadata but never promoted into the base relation vocabulary. Unmatched and multiple matches remain explicit.

## SHADOW_EXPERIMENT boundary

Probe adapter payloads, noncanonical scale definitions, ordered-path storage and relation-set serialization may evolve through WP5.5. They may not weaken object identity, signed-distance convention, source precision, chronology, same-object crossing, scoped completeness or no-hidden-selection. Integrated freeze is operator-required at CEAR-G6.

## Authority and rollback

No active relation selector, scale, threshold, interaction label, detector, formula, release, publication, Validation or downstream authority changes. Relation ledgers and projections are rebuildable; preserve contract, fixtures, crosswalk, QA and decisions. Active C2 remains unchanged.
