# GRT v0.2 Dependency / Companion / Orphan Contract — WP3C

Status: **INACTIVE / NON-ENFORCING**. Authority effect: **NONE**.

A `DependencyContract` declares consumer, provider role, requiredness (`REQUIRED`, `OPTIONAL`, `CONDITIONAL`), cardinality, allowed versions and lifecycle/authority constraints. A required dependency that is missing, ambiguous or incompatible is `UNRESOLVED`; optional absence is typed and lawful. The resolver never selects a “best” provider from ambiguity.

A `CompanionObligation` is satisfied only by a valid, owned, lifecycle-compatible companion with the required relationship. Placeholder/dummy/no-op artifacts cannot satisfy an obligation. `OrphanAssessment` is role-aware: lack of a relationship becomes actionable only for current artifacts under applicable requirements; historical absence alone is not debt. Workflow governance requires explicit owner, purpose, permissions, commands, lifecycle and rollback.

Rule predicates are closed registry identities, not executable expressions. WP3C evaluates them only from explicit caller-supplied semantic facts. Missing mandatory applicability/violation facts are `NOT_EVALUABLE`, never PASS. Actionable violations use the WP2 finding/debt identity and reconciliation machinery; message text, traversal order, paths and timestamps do not define finding identity.

WP3C creates no dependency/provider choice authority, no contract semantic change and no enforcement activation. Reserved provider/semantic choices remain operator-governed.
