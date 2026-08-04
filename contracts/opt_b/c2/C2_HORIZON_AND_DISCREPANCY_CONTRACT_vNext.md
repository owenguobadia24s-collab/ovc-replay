# C2 Horizon, Comparability and Discrepancy Contract vNext r1

Programme: `OVC-C2-ANATOMY-REDESIGN-v0.2`  
Packet: `C2AR-WP2`  
Gate: `CEAR-G2`  
Normative maturity at gate: `NORMATIVE_BOUNDARY`  
Candidate definitions and benchmark adapters: `SHADOW_EXPERIMENT`  
Runtime authority: `SHADOW_ONLY`

## 1. Purpose

This contract separates the observation clock from the evidence horizon. It defines typed horizon identities, causal membership, discontinuity handling, cross-clock comparability, declared-versus-implemented discrepancy evidence and retrospective benchmark isolation. It selects no canonical numeric window and changes no active C2 formula, threshold, selector, clock, lattice, release or historical classification.

## 2. Binding Part 2 decisions

| Decision | Binding rule |
|---|---|
| P2-D1 | Registry time is typed. Every value distinguishes `CALENDAR_DURATION`, `SOURCE_BAR_COUNT`, `OBSERVATION_COUNT`, `SESSION_CLOCK` or `ORDINAL_SLOT` and carries value, unit, grain, version, source basis and applicability scope. A bare number is invalid. |
| P2-D2 | No universal numeric horizon is canonical. Numeric candidate profiles remain `SHADOW_EXPERIMENT` until separately evaluated and frozen. |
| P2-D3 | Observation grain and lattice membership are not measurement horizons. The same observation may participate in multiple clock-specific horizon projections without changing identity. |
| P2-D4 | Causal C2 may use current, transition, backward trailing, paired backward comparison, confirmation delay, run length, age, as-of-parent and closed event-relative horizons. `FORWARD_OUTCOME` is retrospective-only. Centred windows are prohibited. |
| P2-D5 | History-buffer capacity is operational metadata, never a measurement horizon, selector or substitute definition. Insufficient capacity fails closed. |
| P2-D6 | Construction horizons used to create levels or containers belong to those object contracts. A consumer must declare the horizon identity it reads; the horizon registry does not grant construction authority. |
| P2-D7 | Counted causal horizons use contiguous eligible observations within one continuity segment. Session labels and lattice bucket edges do not reset history by themselves; closures, gaps, unknown breaks, explicit resets and partitions do. Wall-clock elapsed time remains separate metadata. |
| P2-D8 | Multiple clock projections coexist. Elapsed-duration, structural-depth and clock-relative-population comparisons are separate declared bases. Bar-count or duration resemblance never creates automatic equivalence. |
| P2-D9 | First-valid time, confirmation delay, persistence/run length and age are separate facts and must not be collapsed into one counter. |
| P2-D10 | Event-relative variable horizons are downstream memberships over already-valid observations. They never replace fixed observations, backdate validity or read past the as-of boundary. |
| P2-D11 | The exact original P2-D11 label is unavailable in the active runtime. The revised plan’s explicit causal-store requirement is binding here: retrospective benchmark outputs and future members must be technically rejected by causal consumers and causal stores. This restatement is source-transparent and grants no additional authority. |
| P2-Q1 | Candidate MOTION windows such as `4/8/16 × 15M`, the legacy-declared `8 × 15M`, and any alternative remain candidates only. Exact selection requires later replay; none is canonical at CEAR-G2. |
| P2-Q2 | Cross-clock equivalence remains unresolved. A mapping must declare whether it compares elapsed duration, structural depth or clock-relative population and must be explicitly registered. |
| P2-Q3 | The default counted horizon uses contiguous eligible observations. Calendar duration around closures is retained as metadata and may be evaluated only by an explicitly typed duration horizon. |
| P2-Q4 | Parent age is defined as an as-of fact now. Any stale/not-stale threshold belongs to Parent Context and Computability policy, not this gate. |

## 3. Horizon identity classes

The registry recognises exactly:

- `CURRENT`
- `TRANSITION`
- `TRAILING_COUNT`
- `PAIRED_COMPARISON`
- `CONFIRMATION_DELAY`
- `RUN_LENGTH`
- `AGE`
- `AS_OF_PARENT`
- `EVENT_RELATIVE_VARIABLE`
- `FORWARD_OUTCOME`

Each definition carries semantic type, unit, grain, source basis, applicability scope, consumers, causal class, continuity policy, first-valid rule, version, optional clock, maturity and an immutable definition hash. Templates may omit candidate counts; executable counted definitions may not.

## 4. Causal classes and first-valid rules

`CAUSAL_CURRENT`, `CAUSAL_BACKWARD`, `CAUSAL_AS_OF` and `CAUSAL_EVENT_CLOSED` may enter causal consumers when their memberships are computable and all member first-valid times are at or before the as-of first-valid time.

`RETROSPECTIVE_ONLY` may enter only research benchmark consumers. Its envelope becomes available only at the final future member’s first-valid time and is marked `causal_store_eligible=false`.

## 5. Membership and discontinuity

A counted membership must remain within one non-null continuity segment and use exact chronological adjacency. It fails closed with an explicit reason for warm-up insufficiency, closure boundary, provider gap/reset, unknown break, partition boundary, partial future window or missing anchor. No member is silently skipped to complete a count.

A current observation that is absent, incomplete, corrupt, closed or otherwise projection-ineligible cannot become a neutral causal measurement.

## 6. Clock-specific horizons

A definition may name a clock or lattice, but the clock only scopes the population; it does not define the semantic horizon. Cross-clock mapping requires one explicit `CrossClockMapping` and one relation basis:

- `ELAPSED_DURATION`
- `STRUCTURAL_DEPTH`
- `CLOCK_RELATIVE_POPULATION`

Mappings are `UNRESOLVED`, `REGISTERED_SHADOW` or `APPROVED_NORMATIVE`. Automatic equivalence is always false. CEAR-G2 approves the mapping protocol, not any numeric equivalence.

## 7. Legacy discrepancy governance

The discrepancy ledger preserves three objects independently:

1. legacy-declared contract;
2. legacy-implemented behavior;
3. redesign candidate.

For MOTION, the preserved contradiction is the declared `8 × 15M / 6 × 2H` evidence population versus an implementation behaving as previous-close transition evidence. For ORGANISATION, it is the declared `16 × 15M / 12 × 2H` population versus an implementation using current-bar range evidence. These are reproducible discrepancy facts, not automatic corrections. Redesign candidates remain non-canonical.

## 8. CEAR-ER1 repository transfer

External research is represented through source, method, transferability and prohibited-inference registries. Only principles incorporated into the governing design scaffold are normative at this gate. Exact external-paper claims, market-specific parameters and benchmark outcomes are not silently reconstructed when source bytes are unavailable.

Transferable methods include point-in-time/as-of chronology, fixed-clock versus event-relative separation, explicit missingness, immutable provenance and leakage controls. Market-specific numeric horizons, automatic cross-clock equivalence and forward labels in causal stores are not transferable without new evidence and authority.

## 9. Benchmark envelope and technical guard

A benchmark envelope records source population, method, comparator, as-of time, availability time and future label members. It is always retrospective-only. `assert_causal_store_record` rejects benchmark-only records, future availability, future members and forward-label fields.

## 10. SHADOW_EXPERIMENT revision boundary

Candidate numeric definitions, comparator payloads, alternative clock mappings, adapter fields and benchmark output shapes may evolve through WP5.5 under a versioned revision ledger. They may not weaken typed identity, causality, chronology, continuity, side separation, explicit comparability or leakage guards. Integrated freeze remains operator-required at CEAR-G6.

## 11. Authority

CEAR-G2 may freeze only the typed-horizon, comparability, discrepancy and causal-store normative boundary. It does not select a numeric horizon, change MOTION or ORGANISATION formulas, reconcile legacy history, activate a clock or lattice, mutate a selector, publish a release, consume Validation or grant probability, risk, exposure, trading, execution or agent-write authority.

## 12. Rollback

Delete and deterministically rebuild horizon populations, comparator outputs and benchmark envelopes. Preserve source/method registries, discrepancy records, cross-clock mappings, fixtures, QA and decisions. Active C2 remains unchanged.
