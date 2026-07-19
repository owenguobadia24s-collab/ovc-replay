# B-STATE-0.3a Operator Review Checklist

**Current status:** Controlled H1 replay candidate; not ratified

Record `APPROVE`, `REVISE` or `REJECT` for each decision:

1. Acceptance is removed from the persistent categorical state vocabulary.
2. Every confirmed acceptance remains a one-bar event at `first_valid_time`.
3. Maintained acceptance is represented as level-specific relations, not an `ACCEPTED_CORRIDOR` label.
4. Every relation and support ID remains visible; floor and ceiling extrema are summaries, not selected authority.
5. Tied floor or ceiling prices retain every tied level ID.
6. Freshness remains numeric—event time and observed-bar age—with no qualitative bucket or TTL.
7. The v0.3 two-failure maintenance exit and range-supersession exit remain unchanged.
8. Acceptance-through retirement stops future level interaction eligibility but does not erase its maintained relation.
9. Different-direction acceptance at different levels may coexist; only same-level contradiction or invalid bounds conflict.
10. Acceptance events and relation measurements cannot suppress displacement, compression or interaction axes.

Ratification would authorize descriptive OPT-B research state only. It would
not activate OPT-C outcomes, edge claims, recommendations or execution.

