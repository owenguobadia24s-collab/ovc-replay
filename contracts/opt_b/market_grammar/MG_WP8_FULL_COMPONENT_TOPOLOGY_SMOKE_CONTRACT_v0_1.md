# MG-WP8 Full Real-Component Topology Smoke Contract v0.1

**Programme:** `OVC-C2E-C2G-C2P-MARKET-GRAMMAR-REMEDIATION-v0.1`  
**Packet:** `MG-WP8`  
**Authority:** inactive, noncanonical `SHADOW_EXPERIMENT` only.

## Purpose

Exercise the implemented market-grammar components as one deterministic vertical slice:

```text
revised C2 boundary
 -> C2E episode ledger
 -> C2G state and transition families
 -> C2G episode families
 -> sensitivity hierarchy and FamilyVariant
 -> episode-derived grammar candidate
 -> immutable noncanonical grammar fixture
 -> C2P parse
 -> typed read-only projection
```

This is a topology and interface smoke, not a promotion or empirical validation run.

## Evidence and mocked-boundary rule

The smoke must use the real repository implementations and frozen registries from MG-WP2
through MG-WP7. It also consumes the accepted MG-WP7 fourteen-candidate migration ledger.

The only mocked market-component boundary is
`REVISED_C2_ACCEPTED_RECORD_SURFACE`. No reproducible real revised-C2 intermediate stream
is committed to the repository for this packet, so a bounded synthetic 15M BID fixture is
used. The fixture is explicitly `SYNTHETIC_NON_AUTHORITATIVE`, contains no outcome/future
fields and grants no market authority.

C2G structural projections for state, transition and episode records are deterministic
fixture adapters over that same bounded revised-C2 surface. They are named
`C2_TO_C2G_STRUCTURAL_PROJECTION_ADAPTER` and are not a new frozen market contract.

## Frozen comparison inputs

- sensitivity packs: existing `MG-C2G-S-0.20-v0.1` and `MG-C2G-S-0.35-v0.1` only;
- clock profile: existing 15M / 2H_A_L shadow comparison profile;
- candidate migration ledger SHA-256:
  `b7873a8ebac5f53f88cf90beed1e00f0ea92488270293ed2a82f2dafafc16733`;
- all fourteen migration dispositions must remain in
  `MAPPED|SUPERSEDED|QUARANTINED|UNRESOLVED` and none may gain promotion authority.

No sensitivity pack is selected as canonical.

## Determinism and restart

The canonical smoke result excludes local path, machine name, wall-clock duration and
other environment values. Two clean executions over the same logical inputs must be
byte-identical. Shuffled C2 input order must converge after lawful chronology sorting.

A checkpoint contains only the logical input SHA-256 and canonical output SHA-256.
Restart recomputes from the frozen logical inputs and must reproduce the exact canonical
output before the checkpoint is accepted. It may not deserialize hidden mutable engine
state.

## Provenance ablation

Family assignment uses structural features only. A separate provenance-inclusive
diagnostic hash may include source/evidence hashes, but provenance may not alter family,
variant or hierarchy assignments. The smoke records both surfaces explicitly.

## Context and parser requirements

- parent first-valid time never exceeds child first-valid time;
- at least one deliberately unmatched child resolves to explicit `UNAVAILABLE`;
- unavailable context is never converted to a neutral predicate;
- every grammar operator in the generated candidate fixture is typed;
- grammar release is noncanonical and unpublished;
- C2P result preserves family/variant distances, phases, missing/conflicting evidence and
  upstream lineage;
- no contradiction is emitted without explicit exclusivity proof.

## Capacity envelope

The retained canonical smoke result must remain below 10 GiB. The focused smoke test must
complete below the programme 14,400-second runtime envelope. Wall-clock duration is QA
evidence only and is excluded from canonical identities.

## Prohibitions

- selector activation or replacement;
- canonical sensitivity, family, variant, rule or grammar selection;
- candidate/family/rule/grammar/theory promotion;
- C3 handoff or semantic authority;
- R2/canonical publication or new immutable release identity;
- Active Discovery, Development or Validation;
- outcome/future-path construction input;
- probability, eligibility, risk, exposure, trading or execution authority.

## Rollback

Remove or supersede the bounded topology-smoke implementation, fixture and derived compact
records. Preserve all completed MG-WP2 through MG-WP7 evidence and their decision records.
No upstream record or external evidence artifact is rewritten.
