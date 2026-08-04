# C2 Observation, Calendar, Lattice and Continuity Contract vNext r1

Programme: `OVC-C2-ANATOMY-REDESIGN-v0.2`  
Packet: `C2AR-WP1`  
Gate: `CEAR-G1`  
Maturity at gate: `NORMATIVE_BOUNDARY`  
Runtime authority: `SHADOW_ONLY`

## 1. Purpose

The observation layer accounts for every declared fixed-clock interval before structural construction or state interpretation. It records expectation, available evidence, continuity and projection eligibility as separate dimensions. It does not choose a level, container, parent, axis state, event, episode or research rule.

## 2. Accepted Part 1 decisions

| Decision | Binding rule |
|---|---|
| P1-D1 | The base C2 observation is a fixed-clock interval record. Event-relative windows are downstream horizon memberships and never replace or backdate the fixed observation. |
| P1-D2 | One nullable `C2.OBSERVATION` exists for every declared interval × instrument × side slot, including closures, absences and corrupt evidence. |
| P1-D3 | Expectation, evidence, continuity and projection eligibility are independent status dimensions. Missing or censored evidence is never converted to neutral, zero, unchanged or false. |
| P1-D4 | `first_valid_time` is the interval end. Anchor or occurrence time never grants earlier causal authority. |
| P1-D5 | BID and ASK have separate slot and observation identities. Cross-side combination requires a separately registered contract. |
| P1-D6 | Closure classification comes only from the versioned OVC instrument calendar and explicit source references. Provider absence cannot infer a scheduled or exceptional closure. |
| P1-D7 | Multiple lattices reference the same physical observation identity. Lattice projection may not copy, repair, synthesise or select observations. |
| P1-Q1 | The authoritative shadow calendar is OVC-owned, versioned, effective-dated and source-linked; the provider is evidence, not calendar authority. |
| P1-Q2 | Weekly/exceptional closure, provider gap, unknown break and partition boundary are different facts. The first eligible observation after a reset starts a new continuity segment. |

## 3. Fixed-clock versus event-relative

A fixed-clock observation has a declared interval start/end, calendar, side and expected-slot identity. It is enumerated whether evidence is present or absent.

Event-relative windows are downstream horizon memberships, not observations. They may later reference one or more observation IDs through a versioned horizon identity. They cannot alter an observation, add future membership or assign a parent.

## 4. Normative record boundary

Every observation contains stable schema, slot, observation and content identities; instrument and side; interval start/end and interval-end first-valid time; partition and calendar references; separate expectation, evidence, projection-eligibility and continuity facts; nullable OPT-A/C1 lineage; lattice membership references; maturity; and explicit zero active authority.

Parent state, future value, outcome, next state, selection result and semantic fields are prohibited.

## 5. Status domains

Expectation: `EXPECTED_EVIDENCE`, `SCHEDULED_CLOSURE`, `EXCEPTIONAL_CLOSURE`, `OUTSIDE_EFFECTIVE_RANGE`.

Evidence: `PRESENT_COMPLETE`, `PRESENT_INCOMPLETE`, `ABSENT`, `CORRUPT`, `UNKNOWN_ABSENCE`, `NOT_EXPECTED`.

Continuity: `SEGMENT_START`, `CONTIGUOUS`, `GAP_RESET`, `CLOSURE_BOUNDARY`, `PARTITION_BOUNDARY`, `UNKNOWN_BREAK`.

Projection is eligible only when expectation is `EXPECTED_EVIDENCE` and evidence is `PRESENT_COMPLETE`.

## 6. Calendar

`OVC.CALENDAR.GBPUSD.NY_1700.v1` is effective-dated and uses `America/New_York`. Its weekly close is Friday 17:00 local through Sunday 17:00 local, so UTC boundaries move with DST. Exceptional closures require explicit interval IDs and source references. Provider absence cannot infer closure. A slot that straddles a calendar boundary fails closed.

## 7. Lattices

Normative profiles are `LATTICE.15M.UTC_0000.v1` and `LATTICE.2H.UTC_0000.v1`. The current experimental profile is `LATTICE.2H.UTC_0100.v1`.

Every membership records an observation ID and bucket bounds. `active` is false. No nearest, best, dominant or fallback lattice exists. Alternative lattice projection references the same observation; it does not copy evidence.

## 8. Continuity

Continuity is evaluated independently per instrument and side. Closed intervals, missing/corrupt/incomplete evidence, unknown absence and partition boundaries terminate the prior eligible segment. A later eligible observation receives `SEGMENT_START`; only exact adjacency within the same live segment receives `CONTIGUOUS`.

## 9. Ledgers and crosswalk

The population ledger exposes declared slot count, observation count, unique slot count and complete status denominators. Every slot is represented exactly once.

Legacy mapping uses exact instrument × side × interval matching. Unmatched records remain explicit null mappings. Historical records are not mutated.

## 10. SHADOW_EXPERIMENT revision

Revision `C2AR.OBSERVATION.SHADOW.r1` may add provisional adapter payloads, alternative-lattice memberships and serialization fields through WP5.5. It may not weaken identity, side separation, causality, chronology, completeness or no-hidden-selection invariants. CEAR-G1 freezes only this normative boundary; integrated experimental detail remains mutable until CEAR-G6.

## 11. Authority

No active selector, clock, lattice, formula, threshold, parameter pack, release, R2 publication, Validation, C2E, C2.5, C3, probability, risk, exposure, trading, execution or agent-write authority is created.

## 12. Rollback

Remove rebuildable vNext observation implementation, projections and ledgers through a new commit. Preserve this contract, fixtures, QA, revision history and legacy crosswalk evidence. Active C2 remains unchanged.
