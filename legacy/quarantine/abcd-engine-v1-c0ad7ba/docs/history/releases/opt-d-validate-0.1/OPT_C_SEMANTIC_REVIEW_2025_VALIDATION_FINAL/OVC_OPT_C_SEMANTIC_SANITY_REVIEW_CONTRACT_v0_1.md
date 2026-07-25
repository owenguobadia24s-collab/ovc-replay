# OVC OPT-C Semantic Sanity Review Contract v0.1

**Review ID:** `OPT-C-SEMANTIC-REVIEW-0.1`  
**Parent:** `OPT-C-MEASURE-0.1.1`  
**Authority:** `DESCRIPTIVE REVIEW ONLY`

## Review axes

1. **Measurement integrity:** exact arithmetic identities, range bounds, timing
   bounds, direction normalization, frontier relations and endpoint-state
   lineage must remain coherent.
2. **Nested-horizon integrity:** excursions, first-hit evidence and transition
   counts cannot reverse or disappear as a complete path extends.
3. **Overlap concentration:** each outcome is labelled `NO_OVERLAP`,
   `SAME_TIME_ONLY`, `SUBSEQUENT_CROSS_CLOCK_ONLY` or
   `SUBSEQUENT_SAME_CLOCK`. Pooled rows remain non-independent.
4. **Cohort support:** support is counted by event clock, horizon, family and
   event direction. Multi-family anchors remain members of each named family;
   cells are not additive.
5. **Frontier applicability:** directional anchors are audited for an available
   primary accepted frontier, retest, loss and endpoint-hold semantics.

## Frozen support bands

| Count | Label | Permitted use |
|---:|---|---|
| 0 | `EMPTY` | No description |
| 1–29 | `SPARSE_NO_COMPARISON` | Inventory only |
| 30–99 | `LIMITED_DESCRIPTIVE_SUPPORT` | Labelled descriptive review |
| 100+ | `ADEQUATE_DESCRIPTIVE_SUPPORT` | Descriptive cohort design |

These bands are visibility controls, not statistical-power claims. They do not
authorize hypothesis tests, threshold selection, optimization or edge claims.

## Gate rules

- Any arithmetic, lineage or nested-horizon violation fails the semantic gate.
- No sparse cell may support a comparison or be silently merged.
- Overlap strata must remain attached to downstream cohort records.
- The 24h horizon remains coverage-only; 48h remains blocked.
- Passing this review permits drafting an OPT-D cohort contract only. It grants
  no outcome interpretation, risk, trading, production or execution authority.
