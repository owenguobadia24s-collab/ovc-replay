# GRT Override Protocol v0.1

**Authority:** operator only

An override is an exact-context, single-use, time-bounded admission exception. It never changes the underlying finding to `PASS`.

Every `ConformanceOverrideRecord` must bind repository, base commit, candidate commit, integration tree, exact finding and rule IDs, rationale, issuer, issue/expiry/remediation times, `max_uses=1`, current use count, and programme-owner visibility. After use, the admitted condition remains `TEMPORARILY_ADMITTED_ACTIONABLE`.

Constitution review is required when override pressure reaches any ratified threshold: three in a rolling 30 days, two affecting one rule family in that period, more than two simultaneously open override debts, or any overdue remediation. Review does not relax enforcement and grants no further override.
