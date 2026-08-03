# OVC Planned-Closure Continuity Remediation Implementation Plan v0.1

## 1. Identity and authority

- **Programme ID:** `OVC-PCCR-v0.1`
- **Plan ID:** `OVC-PLANNED-CLOSURE-CONTINUITY-REMEDIATION-IMPLEMENTATION-PLAN-0.1`
- **Source decision:** `CCR-G5.OPERATOR.PASS.20260803T194600+0100`
- **Initial gate:** `PCCR-G0`
- **Current authority:** plan, contract, fixture, schema, QA and operator-gate preparation only
- **Current authoritative clock:** `2H_A_L_UTC`, unchanged
- **Current authoritative continuity:** strict fail-closed reset handling, unchanged

`PCCR-G0` is operator-required because the proposed work introduces an OVC-owned instrument-calendar dependency and a closure-aware continuity shadow. Neither may be implemented or activated under plan-preparation authority alone.

## 2. Purpose

Determine whether scheduled market closures can be represented separately from provider gaps so that a deterministic, non-canonical continuity lineage can be evaluated without creating bars, repairing prices, changing clock membership or weakening fail-closed provider-gap handling.

The programme addresses one bounded question:

> When the market is known to be closed by an accepted OVC-owned GBPUSD calendar, can a shadow lineage preserve pre-closure analytical history across the closure and materially reduce post-open warm-up loss without changing any observed market record or authoritative C2 state?

The programme does not assume that closure-aware continuity is correct. It must expose exact identity changes, computability gains, contradictions and failure cases before any later activation proposal.

## 3. Binding baseline evidence

The accepted CCR evidence establishes:

- zero 15M or `2H_A_L` clock-grid and M1-membership mismatches;
- 48 provider-gap resets per side;
- four scheduled-market-closure resets per side;
- zero unknown reset causes;
- median LOCATION recovery of 32 bars after provider gaps;
- median LOCATION recovery of 31 bars after scheduled closures;
- 496 side/scope state identities potentially affected by a planned-closure lineage shadow;
- parent context usable for 615 of 4,072 target resolutions (`15.103143%`);
- zero active target `PARENT_RANGE` states.

The external CCR artifact is Google Drive file `17aSvdnbnNivG5efnVnI8PII7veQpBeSx`, 50,836 bytes, SHA-256 `57edecdef747a14ef9d1d27f6dd94f4a7bfb1bfde5035a266cec2144a2e71bfa`.

These are audit baselines, not acceptance thresholds for activation.

## 4. Fixed authority boundaries

### 4.1 Included after `PCCR-G0=PASS`

- an OVC-owned, versioned GBPUSD scheduled-closure calendar for the accepted June evidence scope;
- deterministic classification of scheduled closures versus provider gaps;
- a closure-aware analytical lineage token and shadow resolver;
- shadow-only C1/C2 history-eligibility comparisons using existing formulas and thresholds;
- exact identity, computability, transition and parent-context consequence audits;
- read-only local inspection;
- tests, QA, gate packets, programme state and rollback.

### 4.2 Excluded

- any new instrument, market, side or provider;
- live or prospective provider intake;
- clock replacement, A–L remapping or bar-membership changes;
- interpolation, synthetic bars, price repair or timestamp invention;
- relaxation or reclassification of provider gaps;
- C1/C2 formula, threshold, level, container, relation or axis changes;
- selector, candidate, family, semantic, model or theory promotion;
- C2E or C2.5 resumption;
- Validation consumption, canonical or R2 publication;
- probability, risk, exposure, trading or execution authority;
- continuity activation or release under this plan.

## 5. OVC-owned calendar contract

The calendar must be immutable and versioned. Every entry records:

- calendar and closure identity;
- instrument (`GBPUSD` only);
- UTC scheduled close and scheduled open;
- closure type and source provenance;
- first-valid publication time for the calendar entry;
- observed final pre-close and first post-open source bars;
- boundary-match result and reason codes;
- eligible sides and scopes;
- source hashes and calendar version.

A closure is shadow-eligible only when the calendar entry predates use, scheduled boundaries are complete, observed boundaries are consistent, and no evidence of an open-market provider gap is concealed. Ambiguous or missing calendar evidence fails closed.

The calendar cannot create authority. A calendar entry classifies a known closure; it does not create bars, prices or C2 evidence.

## 6. Closure-aware lineage contract

A shadow lineage may connect the last accepted pre-close analytical history to the first completed post-open observation only when a passing calendar closure record exists.

The lineage:

- preserves the ordered identities of observed bars and states;
- records the closure interval explicitly rather than treating it as elapsed observed bars;
- creates no bars or state values inside the closure;
- does not advance rolling counters during the closure;
- becomes first-valid no earlier than the first completed post-open observation;
- terminates immediately on a provider gap, malformed adjacency, unknown discontinuity or calendar mismatch;
- carries `SHADOW_ONLY`, `NON_CANONICAL`, `NON_PROMOTABLE`, `NO_ACTIVATION`.

The authoritative strict-reset lineage remains available and unchanged for every comparison.

## 7. Required comparisons

Exactly two continuity views are permitted:

1. `V0_CURRENT_STRICT_CONTINUITY_AUTHORITATIVE`
2. `V1_SCHEDULED_CLOSURE_LINEAGE_SHADOW_ONLY`

No parameter search, third continuity variant or observed-result-selected configuration is allowed.

The full-population comparison must report, with exact denominators:

- scheduled closures classified, rejected and ambiguous;
- provider gaps preserved as strict resets;
- state identities unchanged versus potentially changed;
- axis-level and full-vector evaluability;
- post-open warm-up bars and elapsed time;
- transition count and first-valid-time differences;
- parent-context and `PARENT_RANGE` availability;
- BID/ASK and local/with-parent duplication;
- all calendar, source and identity mismatches;
- runtime, checkpoints and retained artifact size.

A computability gain is not semantic, predictive or activation evidence.

## 8. Work packets

### PCCR-00 — Plan and authority freeze

Deliver this plan, authority/design contract, schema, non-evidentiary fixture, programme state, QA packet and `PCCR-G0` decision packet.

**Gate `PCCR-G0`: OPERATOR_REQUIRED.** PASS authorises bounded calendar materialisation and closure-aware shadow implementation only. It does not change active continuity.

### PCCR-WP1 — Calendar and classification foundation

Materialise the OVC-owned GBPUSD calendar for the accepted June scope. Bind all scheduled closures to source evidence and hashes. Produce positive, negative, ambiguous, provider-gap and boundary-mismatch fixtures.

Any inability to reproduce four scheduled closures per side, or any provider-gap reclassification, blocks continuation.

### PCCR-WP2 — Deterministic shadow lineage resolver

Implement the closure-aware lineage token and resolver. Enforce first-valid timing, zero invented observations, no counter advancement during closure and immediate fail-closed termination on non-calendar discontinuity.

### PCCR-WP3 — Full-population shadow reconstruction

Run V0 and V1 over the accepted June population. Outputs remain local, non-canonical and non-promotable. No raw market data or full populations are committed to Git.

### PCCR-WP4 — Consequence and identity audit

Audit the 496 potentially affected side/scope identities and all observed consequences. Report gains, losses, contradictions, unchanged records and sensitivity by side, scope, week, A–L block and closure identity.

### PCCR-WP5 — Read-only review surface

Add a local read-only route exposing calendar provenance, closure decisions, V0/V1 lineage, exact changed identities, not-evaluable reasons and all authority denials. No annotation, acceptance, activation or mutation controls.

### PCCR-WP6 — Final disposition packet

Produce one consolidated operator packet with allowed decisions `PASS`, `DEFER`, `BLOCK`, `QUARANTINE` or `SUPERSEDE`.

**Gate `PCCR-G6`: OPERATOR_REQUIRED.** A PASS may authorise preparation of a separate activation/release plan only. It cannot activate closure-aware continuity directly.

## 9. Acceptance conditions

- exact reproduction of the CCR reset census and baseline metrics;
- exactly four scheduled closures per side in the accepted scope, or a blocking discrepancy record;
- zero provider gaps classified as scheduled closures;
- zero unknown reset causes hidden or repaired;
- zero synthetic bars, interpolated prices or invented timestamps;
- unchanged 15M and `2H_A_L` bar identities and memberships;
- no formula, threshold, selector or release drift;
- first-valid closure lineage no earlier than the first completed post-open observation;
- deterministic lineage and changed-identity hashes;
- complete V0/V1 denominator accounting;
- all 496 potentially affected state identities resolved as changed, unchanged, ineligible or mismatch;
- complete repository tests and OVC `FINAL_HEAD` assurance;
- QA recommends PASS with no blocking warning or unresolved authority escape.

## 10. Capacity and artifacts

Each packet is bounded to four hours local runtime and 10GB retained external artifacts. Long scans checkpoint at least every 30 minutes. `CAPACITY_EXCEEDED` preserves completed partitions and stops without sampling, threshold changes or scope reduction.

Raw market data, caches and full shadow populations remain external and content-addressed.

## 11. Automatic continuation

After `PCCR-G0=PASS`, packets PCCR-WP1 through PCCR-WP5 may auto-ratify and squash-merge when acceptance conditions, tests and QA pass and the authority delta remains wholly non-reserved. Stop immediately for calendar scope expansion, continuity activation, provider-gap relaxation, formula/threshold change, non-reproducible evidence or any other reserved authority.

## 12. Rollback

Disable and discard closure-aware shadow resolvers and derived outputs while preserving the calendar versions, source hashes, audit evidence, findings, decisions and negative results. V0 strict continuity remains authoritative throughout. No history is rewritten and no accepted evidence is deleted.

## 13. Work after `PCCR-G0` approval

Build the bounded calendar and classification foundation, implement the shadow lineage resolver, run the full-population V0/V1 comparison, audit all identity and computability consequences, attach the read-only review surface, generate QA and stop at `PCCR-G6`.
