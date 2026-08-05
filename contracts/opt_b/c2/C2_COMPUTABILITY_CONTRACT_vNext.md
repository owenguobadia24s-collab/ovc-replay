# C2 Computability, Consumer Eligibility, Denominator and Overlap Contract vNext

Status: `SHADOW_FROZEN_READ_ONLY`  
Authority: inactive, noncanonical shadow implementation admitted by `CEAR-G9` only.

## 1. Separate dimensions

Every component or operation records five independent dimensions:

1. **Availability** — `AVAILABLE`, `UNAVAILABLE` or `NOT_REQUESTED`.
2. **Technical computability** — `COMPUTABLE`, `NOT_COMPUTABLE`, `NOT_APPLICABLE`, `CENSORED` or `CONFLICTED`.
3. **Assurance** — `ASSURED`, `UNASSURED`, `CONFLICTED` or `NOT_ASSESSED`.
4. **Consumer eligibility** — `ELIGIBLE`, `INELIGIBLE` or `NOT_EVALUATED` for one exact consumer-policy identity.
5. **Authority** — `AUTHORIZED` or `UNAUTHORIZED`.

No dimension implies another. Computable evidence may remain unassured, ineligible or unauthorized.

## 2. Dependency graphs

Dependency graphs are versioned and profile-specific. Allowed edge types are:

- `REQUIRED`: failure blocks only the exact dependent component.
- `OPTIONAL`: failure records a warning and does not block the raw component.
- `WARNING_ONLY`: failure has no computability effect.
- `ALTERNATIVE`: at least one member of the exact named group must be successful.
- `PROHIBITED`: presence creates `CONFLICTED` evidence.

Every dependency identity, result and propagated reason remains visible. No global failure propagation, hidden substitute or fallback is permitted.

## 3. Terminal dispositions and reasons

`NOT_REQUESTED`, `NOT_APPLICABLE`, `NOT_COMPUTABLE`, `CENSORED` and `CONFLICTED` are distinct. Warm-up insufficiency, missing sources, continuity gaps, censorship, ambiguity, staleness evidence, model absence, dependency failure, conflicts and authority denial use explicit reason codes. None may be silently converted to zero, neutral, unchanged or false.

## 4. Axis and parent effects

LOCATION profiles have separate local, structural and parent dependency graphs. Raw MOTION and normalized MOTION are separate components. ORGANISATION remains independently computable by metric. INTERACTION remains bound to exact object and track identities. Parent absence affects only profiles declaring a required parent dependency.

## 5. Consumer eligibility

Each consumer policy is versioned, inactive and noncanonical. Eligibility is evaluated per component and exact consumer. It requires technical computability and lawful consumer authority. A consumer may require assurance and named raw age dimensions. This contract selects no active consumer and no numeric staleness or freshness threshold.

## 6. Denominator accounting

Every population record declares scope, unit, consumer policy, dependency graph, release, calendar, clock/lattice, overlap policy and censorship/conflict treatment. Required counts are:

`population`, `requested`, `not_requested`, `applicable`, `not_applicable`, `available`, `computable`, `not_computable`, `censored`, `conflicted`, `assured`, `eligible`, `included`, `numerator`, `denominator`.

Required identities:

- population = requested + not requested;
- requested = applicable + not applicable;
- applicable = computable + not computable + censored + conflicted;
- eligible ≤ computable;
- included ≤ eligible;
- numerator ≤ denominator.

Raw counts remain separate from rates. Transition rates use comparable transition pairs, not individual observations. Mixed-unit rates are prohibited.

## 7. Claim-specific overlap

Raw units are immutable. Cluster evidence may identify shared observations, windows, object tracks, bundles, explicit BID/ASK pairs or separately authorized episodes. Every adjusted claim must identify its exact claim, unit, cluster policy and membership. This implementation reports raw and cluster counts only; it selects no canonical weighting, deduplication or numeric adjustment.

## 8. Comparability

Population results are comparable only when unit, scope, instrument, side handling, release, calendar, clock/lattice, dependency graph, consumer policy, eligibility version, denominator definition, overlap policy and censorship/conflict treatment match. Otherwise the result is `NOT_COMPARABLE` with exact mismatch reasons.

## 9. Legacy QUALITY projection

A legacy QUALITY compatibility projection may expose component counts and reasons. It is non-governing, has no global quality state, cannot hide component evidence, and cannot drive eligibility or denominator inclusion.

## 10. Prohibited authority

This contract grants no active or canonical consumer, numeric staleness threshold, canonical overlap adjustment, active rate publication, global QUALITY gating, semantic event or episode authority, C2E/C2.5/C3 authority, rule or theory promotion, provider intake, canonical/R2 publication, Validation use, active C2 change, probability, risk, exposure, trading, execution or agent write.

Changes require a new version and supersession record. Active legacy C2 remains unchanged.
