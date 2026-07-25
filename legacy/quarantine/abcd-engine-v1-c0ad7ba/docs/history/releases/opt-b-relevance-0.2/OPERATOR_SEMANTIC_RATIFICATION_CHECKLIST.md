# OPT-B Semantic Ratification Checklist

**Scope:** `B-REF-0.2` and H1 GBP/USD review  
**Decision status:** Open

## A. Range supersession

- Does a newer rolling eight-bar `RANGE_HIGH` or `RANGE_LOW` replace the prior
  boundary as the current local-range reference?
- Should the retired boundary remain retrievable as history but become
  ineligible for new classifications?
- Are same-price successor boundaries distinct observations or reinforcements
  that should share a compound reference?

## B. Acceptance-through retirement

- Does confirmed four-bar acceptance beyond a level mean the old level has
  ceased to describe the current price story?
- Is retirement correctly effective at confirmation time, while preserving the
  acceptance episode whose anchor preceded confirmation?
- Should a later return create a new level/story event rather than reactivate
  the retired level?

## C. Compound states

- Approve representing same-label agreement as
  `STATE {level_id_1, level_id_2, ...}` rather than `AMBIGUOUS`.
- Keep `AMBIGUOUS` when top-precedence semantic labels conflict, for example
  simultaneous `ACCEPTED_ABOVE` and `ACCEPTED_BELOW`.
- Do not introduce nearest-level, strongest-level or hidden-best selection.

## D. Maximum age

- Keep maximum-age retirement disabled for the next replay unless there is a
  semantic reason a structurally active level must expire.
- Retain 8h/24h/48h/72h as comparison variants until more closed periods are
  reviewed.

## E. Thresholds

- Keep `B-LANG-0.1-SEED` frozen for the next replay.
- Treat compression as provisional because its count changes sharply across
  nearby threshold profiles.
- Require a full response-window replay before changing level-term distances.

## F. Required operator decisions

Record `APPROVE`, `REVISE` or `REJECT` for:

1. Same-type range supersession.
2. Acceptance-through retirement.
3. Permanent no-reactivation in v0.2.
4. Compound same-label multi-level states.
5. `STRUCTURAL_ONLY` as the next-replay policy.
6. Continued freeze of `B-LANG-0.1-SEED` thresholds.

Approval applies only to research replay. It does not activate trading,
OPT-C outcomes, edge claims or execution.
