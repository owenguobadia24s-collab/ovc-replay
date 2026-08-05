# CEAR-G9 — Computability, Consumer Denominator and Overlap Policy Freeze

**Programme:** `OVC-C2-ANATOMY-REDESIGN-v0.2`  
**Plan:** `OVC-C2-ANATOMY-REDESIGN-IMPLEMENTATION / 0.2-REVISED`  
**Packet:** `C2AR-WP9`  
**Baseline main:** `8ef7efb131a87ee9304c8e41494d64980dbc875d`  
**Authority:** **OPERATOR REQUIRED**  
**Recommended decision:** **PASS**

## Decision

Approve a versioned computability, consumer-eligibility, denominator, overlap and comparability policy for later **inactive, noncanonical, read-only shadow implementation only**.

The central rule is:

> Usability is per component and per exact consumer. It is not one global degraded or QUALITY state.

Five dimensions remain separate:

1. **Availability** — whether the exact requested source object exists.
2. **Computability** — whether the exact component can be deterministically produced under its declared dependency graph.
3. **Assurance** — whether the produced evidence passed its declared checks.
4. **Consumer eligibility** — whether one exact registered consumer accepts the component.
5. **Authority** — whether that consumer is lawfully permitted to use it.

No dimension grants another. An available value may be non-computable; a computable value may be unassured; an assured value may be ineligible; and an eligible value remains unusable when authority is absent.

## Component and dependency policy

Computability is recorded by component, profile and observation or unit. Dependency graphs are versioned and profile-specific. Their only edge types are:

- `REQUIRED` — failure propagates only to the exact declared dependent;
- `OPTIONAL` — failure records a warning without making the component non-computable;
- `WARNING_ONLY` — no computability effect;
- `ALTERNATIVE` — at least one member of the exact named group must be computable;
- `PROHIBITED` — presence fails closed.

Every dependency and propagated reason remains visible. No hidden fallback exists, and one failed component cannot collapse unrelated axes.

The axis rules remain separate:

- LOCATION profiles separately depend on local trailing, local structural, parent measurement or parent structural context.
- Raw MOTION requires its declared sequence and continuity; normalized MOTION additionally requires one exact named scale.
- ORGANISATION may be partial by metric, with every metric’s result exposed.
- INTERACTION is computable per exact object and track.
- Missing parent context affects only profiles that declare a required parent dependency.
- Global QUALITY is retired as a governing state. A compatibility projection may remain only when it transparently exposes every source component and reason and cannot drive eligibility or denominator inclusion.

## Missingness and reason evidence

The terminal dispositions remain distinct:

- `NOT_REQUESTED`
- `NOT_APPLICABLE`
- `COMPUTABLE`
- `NOT_COMPUTABLE`
- `CENSORED`
- `CONFLICTED`

Warmup, population insufficiency, source missingness, continuity gaps, censorship, ambiguity, staleness, model absence, dependency failure, conflict and authority denial use separate reason-code families. No missing, censored, ambiguous or conflicted unit may be silently removed.

## Consumer eligibility and staleness

Eligibility is evaluated separately for each exact consumer-policy identity. The same component can be eligible for one consumer and ineligible for another. Eligibility requires computability and lawful authority; each consumer declares whether assurance is required.

A consumer that uses age must identify its staleness policy and retain the raw age evidence produced by WP8. CEAR-G9 selects **no universal or numeric staleness or freshness threshold** and activates no consumer policy.

## Denominator accounting

Every rate or proportion must identify:

- registered scope;
- compatible unit type;
- consumer policy;
- numerator and denominator definitions;
- overlap policy;
- censorship and conflict treatment;
- population, requested, not-requested, applicable, not-applicable, available, computable, non-computable, censored, conflicted, assured, eligible, included, numerator and denominator counts.

The accounting identities are explicit:

- population = requested + not requested;
- requested = applicable + not applicable;
- applicable = computable + not computable + censored + conflicted;
- eligible ≤ computable;
- included ≤ eligible;
- numerator ≤ denominator.

Availability, assurance and authority counts are orthogonal and cannot replace the terminal-disposition partition. Raw counts remain separate from rates. Transition rates use comparable **transition pairs**, not individual observations. Mixed-unit rates are prohibited.

## Overlap and comparability

Overlap is claim-specific. Raw units are always preserved. Supported evidence clusters are shared observations, windows, object tracks, bundles, explicit BID/ASK pairs and—only after separate episode authority—shared episodes.

A cluster-adjusted claim requires an exact cluster-policy ID, claim definition, unit and membership evidence. CEAR-G9 selects no canonical weighting, deduplication or numeric overlap adjustment. Raw and adjusted rates cannot be mixed, and adjusted comparisons require the same policy ID, unit and claim definition.

Comparisons require compatible unit, scope, instrument, side handling, release, calendar, clock/lattice, dependency graph, consumer policy, denominator, overlap and censorship/conflict treatment. Otherwise the result is `NOT_COMPARABLE` with exact reasons. Cross-side pooling is prohibited unless the unit is an explicitly registered BID/ASK pair.

## Explicit exclusions

This decision does not grant:

- active or canonical consumer eligibility;
- numeric staleness or freshness thresholds;
- canonical overlap weighting, deduplication or adjustment;
- active rate or denominator publication;
- global QUALITY gating;
- hidden fallback or silent exclusion;
- semantic event or episode promotion;
- C2E or C2.5 activation;
- rule or theory promotion;
- provider intake;
- canonical or R2 publication;
- Validation consumption;
- active C2 selector or release changes;
- probability, risk, exposure, trading, execution or agent-write authority.

## Evidence and rollback

The machine-readable packet is `CEAR_G9_GATE_PACKET.json`. The candidate policy is `registries/opt_b/c2/vnext/C2_COMPUTABILITY_CONSUMER_POLICY_CANDIDATE_v0_1.jsonc`.

Required before decision readiness: gate-policy tests, complete repository suite, FINAL_HEAD assurance, merge readiness, zero unresolved review threads and proof that active and downstream authority remains unchanged. No external artifact, market data or R2 write is required.

Before approval, close this PR unmerged and retain WP8 main. After approval, preserve the immutable decision and supersede it only through a new versioned operator record. A later shadow implementation can be disabled without active C2 rollback.

## Exact work after PASS

Record and merge the CEAR-G9 decision; implement the policy only as inactive, noncanonical shadow machinery; run complete assurance; auto-ratify and squash-merge `C2AR-G9A` only when all acceptance conditions pass; seal the receipt; then prepare CEAR-G10 rule-reconstruction dispositions and stop.

## Operator command

`OVC APPROVE CEAR-G9 PASS`
