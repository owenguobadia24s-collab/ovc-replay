# OVC Market Translation and Option-Flow Audit

## Revised Implementation Plan v0.2

**Plan ID:** `OVC-MARKET-TRANSLATION-OPTION-FLOW-AUDIT-IMPLEMENTATION-PLAN-0.2`  
**Programme ID:** `OVC-MTA-v0.2`  
**Prepared:** 2 August 2026  
**Source attachment SHA-256:** `bd8fd1bea923e3bb5bc5cf19487ca4c545b78c21e4299d1a80878eb94c9c640d`  
**Source attachment bytes:** `560459`  
**Status:** `OPERATOR_RATIFIED_MTA_G0_PASS`

## Authority notice

This plan authorises repository design and bounded audit implementation after operator ratification. It does not authorise provider intake, formula or threshold changes, clock replacement, active-selector mutation, C2E activation, C2.5 event promotion, C3 semantic promotion, R2 canonical publication, Validation consumption, probability, exposure, trading, execution or agent write authority.

## Executive decision

Replace immediate operator effort on the forty-card June blinded review with a governed, capacity-bounded audit over the complete June population. Preserve the blinded-review package and RO4 evidence as separate records. Classify the current Option flow, measure translation and computability, construct overlap-aware independence units, and prepare separately governed readiness evidence for clock/continuity, C2E, C2.5 and C3.

The audit observes but does not modify:

```text
OPT-A sealed observations
  -> OPT-B.C1 atomic facts
  -> OPT-B.C2 levels, containers, relations, states, transitions and quality
  -> MTA marker population and overlap-aware audit units
  -> non-authoritative readiness evidence for C2E, C2.5 and C3
```

RO4 sequence windows and friction records remain separate analytical objects and may only be referenced as supporting or contradicting evidence.

## Binding governance corrections

1. **Capacity contract:** one packet attempt has a maximum expected local wall-clock runtime of four hours and may retain no more than 10GB of new external artifacts. Deterministic sharding, checkpoints and `CAPACITY_EXCEEDED` recovery are mandatory.
2. **Registry amendments:** classifications may not be edited in place. Material errors create an immutable `REGISTRY_AMENDMENT`, operator acknowledgement, a new registry version and deterministic reruns.
3. **C2.5 presentation:** criterion-level evidence and counts are shown by default. A recommendation may appear only beneath the evidence and is not an authority badge.
4. **Cluster sensitivity:** exactly three variants are frozen: strict overlap, primary overlap plus one 15M interval, and permissive overlap plus four 15M intervals. The primary variant alone is authoritative.
5. **Decomposed final gate:** `MTA-G8-CLOCK`, `MTA-G8-C2E`, `MTA-G8-C2.5` and `MTA-G8-C3` receive independent operator decisions.
6. **RO4 integration:** object identities and promotion paths remain separate. Contradictory conclusions produce `CROSS_PROGRAMME_INCONSISTENCY`.
7. **Supervised continuation:** automatic continuation stops at `MTA-A3` after WP3 and `MTA-A6` after WP6.

## Baseline

- Repository: `owenguobadia24s-collab/ovc-replay`
- Plan baseline main: `d8a7f07f5abe376b917cf6f95f6e9ccc1864b7c3`
- Resumed MTA-G0 base main: `544dc2f6477ce415321f9419a62586fcffa0d02c`
- Accepted June replay: `PD-JUNE-FM.RUN.9810cfa8a2e2930be2e503b9`
- June target: `[2026-06-01T00:00:00Z, 2026-07-01T00:00:00Z)`
- Context slice: `RPS.DUKASCOPY.GBPUSD.20260530_20260703.v1`
- Target records: 4,526 C1; 8,598 C2 states; 6,783 C2 transitions
- Review population: 7,116 eligible windows; 13,993 rule-level not-evaluable markers
- PR #202: open, unmerged, preserved as an external-review construction source only
- PR #209: merged; its reproducible main-ruleset evidence resolves the prior MTA-G0 ruleset blocker
- RO4: separate sequence-evidence programme, currently blocked at RO4-G6 pending evidence accumulation

## Current flow classes

| Namespace | Grain | Current authority | Lawful downstream role |
|---|---|---|---|
| OPT-A | sealed source interval | market truth | parent of C1 |
| OPT-B.C1 | one closed-bar primitive record | derived fact | parent of C2 |
| OPT-B.C2.L | first-valid reference level | structural context | containers, relations, states |
| OPT-B.C2.K | active bounded container | structural context | state and sequence evidence |
| OPT-B.C2.R | bar/scope relation set | structural fact | interaction and evidence |
| OPT-B.C2.S | parallel state vector | descriptive state | transitions and later research |
| OPT-B.C2.T | consecutive-state transition | temporal fact | markers and sequence evidence |
| OPT-B.C2.Q | quality/computability | assurance evidence | constrains all consumers |
| MTA.MARKER | timestamp/rule result | research diagnostic | population and routing evidence |
| MTA.OCCURRENCE | collapsed market interval | derived audit unit | parent of clusters |
| MTA.OVERLAP_CLUSTER | connected interval component | derived independence unit | frequency/readiness unit |
| RO4.SEQUENCE_WINDOW | RO4 sequence | separate research evidence | support/contradiction only |
| RO4.FRICTION_RECORD | RO4 boundary friction | separate research evidence | support only; insufficient alone |
| OPT-B.C2E | variable-duration episode | deferred | possible parent of events/C3 |
| OPT-B.C2.5 | deterministic event | blocked | separately ratified only |
| OPT-B.C3 | reviewed structural meaning | blocked | requires stable lawful inputs |

## Programme sequence

| Packet | Branch | Output | Next control |
|---|---|---|---|
| MTA-00 | `gate/mta-g0-ratification-resume` | baseline, authority, capacity, cluster, amendment, RO4 and June-review disposition packet | MTA-G0 |
| MTA-WP1 | `audit/mta-wp1-flow-registry` | current-flow contract, object/metric/reason registries and audit schemas | MTA-G1 |
| MTA-WP2 | `audit/mta-wp2-source-c1` | OPT-A coverage and C1 translation audit | MTA-G2 |
| MTA-WP3 | `audit/mta-wp3-c2-translation` | C2 levels, containers, relations, axes, persistence and transitions audit | MTA-G3 then MTA-A3 |
| MTA-WP4 | `audit/mta-wp4-clock-parent` | A-L and parent-resolution audit | MTA-G4 |
| MTA-WP5 | `audit/mta-wp5-marker-population` | full marker/non-evaluable populations and matrices | MTA-G5 |
| MTA-WP6 | `audit/mta-wp6-overlap-independence` | strict/primary/permissive clusters and sensitivity | MTA-G6 then MTA-A6 |
| MTA-WP7 | `audit/mta-wp7-readiness-surface` | RO4 comparison, readiness evidence and read-only console routes | MTA-G7 then four G8 decisions |

After MTA-G0, WP1-WP3 may continue through passing non-reserved gates and then stop at MTA-A3. After acknowledgement, WP4-WP6 may continue and then stop at MTA-A6. After acknowledgement, WP7 may continue to MTA-G7 and then stop once with four independent operator decisions.

## Packet summaries

### MTA-WP1 - current flow registry

Freeze the object, metric and reason-code registries; distinguish all computability statuses; classify each current marker functionally; prohibit current markers from inheriting C2.5 authority; implement immutable registry amendments and supersession maps.

### MTA-WP2 - OPT-A and C1 translation

Account for every lawful June source interval and C1 record. Classify complete intervals, provider gaps, scheduled closures, source partition boundaries, incomplete buckets, missing sides and corrupt/unknown discontinuities. Verify exact parentage, formula identity, serialization, contiguity and deterministic rerun.

### MTA-WP3 - C2 structural translation

Audit RANGE_HIGH, RANGE_LOW, MIDPOINT, SWING_HIGH, SWING_LOW, LOCAL_RANGE, PARENT_RANGE, SWING_ENVELOPE, relations, five state axes, persistence, transitions and reset warm-up. Every accepted C2 ID must reconstruct or have an exact source-resolved reason. Stop at MTA-A3.

### MTA-WP4 - 2H clock and parent context

Build the parent-link ledger, A-L block mapping, parent age, refresh, boundary distance and reset-cause census. Separate scheduled closure, provider gap, partition and unknown resets. Any clock recommendation remains non-activating evidence for MTA-G8-CLOCK.

### MTA-WP5 - marker population

Re-evaluate every rule and publish attempted, evaluable, fired, not-fired and not-evaluable populations. Calculate window, full-vector and parent usability rates with exact denominators. Classify markers as state-change, level-interaction, persistence, sequence-instability, cross-scale context, computability or research-selection-only.

### MTA-WP6 - overlap and independence

Collapse identical centre times across BID/ASK and local/with-parent scopes. Build interval-graph connected components under exactly three variants. Use `PRIMARY_OVERLAP_PLUS_1` for authoritative counts and classify sensitivity as ROBUST, MATERIAL_SENSITIVITY or STRUCTURALLY_UNSTABLE. Stop at MTA-A6.

### MTA-WP7 - readiness routing

Create criterion-level evidence for C2E, each C2.5 rule and C3. Reference RO4 separately, surface contradictions, and expose read-only `/flow`, `/translation`, `/computability`, `/context`, `/markers`, `/clusters`, `/ro4-comparison`, `/readiness` and `/capacity` routes. No route grants write or activation authority.

## MTA-G0 mandatory operator decisions

The operator explicitly decided:

1. ratify this audit-only plan;
2. set `PD-JUNE-FM-G2` to `DEFER` without recording a blinded-review outcome;
3. preserve PR #202 open and unmerged without deleting its branch or external artifacts;
4. approve the four-hour/10GB capacity contract and shard/checkpoint rules;
5. approve the three frozen cluster variants;
6. approve the MTA-RO4 separation and inconsistency rules;
7. require MTA-A3 and MTA-A6 acknowledgements;
8. accept the pinned June WP2/WP3/RO4 source inventory;
9. freeze the June target population and deny Validation/new provider data.

## Final operator decisions

- `MTA-G8-CLOCK`: whether to prepare a separate clock/continuity review plan.
- `MTA-G8-C2E`: whether to prepare a neutral episode-layer plan.
- `MTA-G8-C2.5`: per-rule or bounded-rule-set decisions on event-contract design.
- `MTA-G8-C3`: whether semantic-design work is warranted.

A PASS authorises preparation of the named separate plan only. It activates nothing.

## Capacity recovery

On `CAPACITY_EXCEEDED`: stop before the bound, close outputs, hash completed shards and cursor state, create a non-authoritative checkpoint and incident, delete only replaceable temporary material, resume under the frozen shard hierarchy, recombine deterministically and rerun QA. Block only when the smallest lawful shard exceeds the bound, required retained evidence cannot fit under 10GB, or recombination is not reproducible.

## Mandatory stops

Stop for selector/release/Validation/parameter changes; clock replacement or continuity changes; C2E/C2.5/C3 activation; material registry amendments awaiting acknowledgement; MTA-A3 or MTA-A6; material RO4 inconsistency awaiting review; irreducible capacity failure; missing source artifacts; unsafe repository state; uncorrectable QA failure; or the four-part MTA-G8 packet.

## Rollback

Revert only bounded audit implementation through new non-destructive commits. Preserve source records, all registry versions and amendments, checkpoints, audit ledgers, incidents, QA, decisions, acknowledgements and external hashes. No rollback deletes negative evidence or reactivates superseded semantics.
