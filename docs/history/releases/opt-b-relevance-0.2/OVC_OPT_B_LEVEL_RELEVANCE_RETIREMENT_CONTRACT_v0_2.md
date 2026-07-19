# OVC OPT-B Deterministic Level Relevance and Retirement Contract v0.2

**Contract ID:** `B-REF-0.2`  
**Initial sensitivity seed:** `B-REF-0.2-SEED`  
**Scope:** GBP/USD BID, sealed 15M and fixed-UTC 2H bars  
**Status:** `DRAFTED FOR HISTORICAL REVIEW — NOT ACTIVE`

## Purpose

`B-REF-0.1` defines when a reference level first becomes knowable. This contract
defines the bounded interval during which that known level may participate in an
OPT-B classification. It changes relevance only; it never changes the source
price, level price, creation lineage or first-valid time.

## Lifecycle

```text
NOT_YET_VALID → RELEVANT → RETIRED
```

- A level becomes `RELEVANT` at its existing `first_valid_time`.
- A level is eligible for a candidate bar only when
  `first_valid_time <= candidate.open_time < retired_at`.
- `retired_at` is exclusive and is never backdated.
- Retirement is permanent in v0.2. A later structurally similar level receives
  its own deterministic level ID; old levels are never silently reactivated.
- Gaps, weekends and missing buckets do not themselves retire a level.

## Retirement triggers

The effective retirement time is the earliest deterministic trigger:

1. `ACCEPTED_THROUGH` — the first confirmed four-bar acceptance beyond the
   level. Retirement becomes effective at the acceptance record's
   `first_valid_time`. The acceptance episode remains admissible because its
   anchor preceded retirement.
2. `RANGE_SUPERSEDED` — for `RANGE_HIGH` and `RANGE_LOW`, the next level of the
   same type and construction rule retires the prior boundary at the newer
   level's `first_valid_time`.
3. `MAXIMUM_AGE` — a deterministic elapsed-UTC-time safety cap measured from
   `first_valid_time`.

If triggers share a timestamp, precedence is `ACCEPTED_THROUGH`, then
`RANGE_SUPERSEDED`, then `MAXIMUM_AGE`. The trigger ID and reason are recorded.

## Seed maximum ages

| Level family | Maximum age | Rationale |
|---|---:|---|
| Rolling eight-bar range | 8 hours | A current local range boundary is short-lived and is normally superseded sooner. |
| Confirmed 2×2 swing | 48 hours | Matches OVC's approved initial maximum holding and decision horizon. |

Elapsed UTC time is used deliberately. Accepted-bar age would make a level's
lifetime depend on data sparsity; automatic gap retirement would confuse source
absence with market meaning.

## Deterministic identity

Each lifecycle record hashes:

- `B-REF-0.2` version;
- level ID and policy ID;
- relevance start and retirement timestamp;
- retirement reason and trigger ID.

The underlying `B-REF-0.1` level ID remains unchanged.

## Prohibited behaviour

The relevance engine must not:

- rank levels using future outcomes;
- choose a hidden best level;
- infer retirement from profitability;
- retire a level because source bars are missing;
- modify historical classification anchors;
- reactivate a retired level;
- promote this seed policy without semantic review and operator approval.

## Review variants

The seed must be compared with:

| Variant | Range rule | Swing rule | Purpose |
|---|---|---|---|
| `NO_RETIREMENT` | None | None | Historical baseline |
| `STRUCTURAL_ONLY` | Supersession/acceptance | Acceptance | Isolate structural triggers |
| `TIGHT_24H` | 8-hour cap | 24-hour cap | Test stronger recency |
| `SEED_48H` | 8-hour cap | 48-hour cap | Initial operating-frame hypothesis |
| `RELAXED_72H` | 12-hour cap | 72-hour cap | Test slower structural memory |

No variant may be selected using OPT-C outcomes during this review. Selection
is based only on semantic coherence, ambiguity, stability and operational
simplicity. Edge assessment remains a later OPT-C/OPT-D activity.

## Post-review recommendation

The H1 review recommends `STRUCTURAL_ONLY` for the next controlled replay:

- range levels retire on same-type supersession;
- all levels retire on first confirmed acceptance-through;
- no maximum-age retirement is active yet.

This policy reduced mean active levels from 5,773 to 3.83 at 15M and from 751
to 4.10 at 2H. Ambiguity fell from 58.51% to 8.38% and from 47.47% to 8.74%
respectively. Only one 15M level and two 2H levels remained unretired by the
end of the sealed period.

The 8-hour/48-hour caps are retained as sensitivity hypotheses. They did not
materially improve 15M ambiguity and caused 194 bars at each clock to have no
active reference level. A TTL should not become canonical until additional
closed periods show that the remaining structurally active levels are stale.
