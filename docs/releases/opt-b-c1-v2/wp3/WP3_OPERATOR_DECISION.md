# OPT-B.C1 v2 WP3 Operator Decision

## Decision

`PASS — REFERENCE ENGINE AND FIXTURE TRUST`

## Reviewed baseline

- WP2 primitive contract, formula registry, null policy, input profile and schemas are frozen.
- Formula registry: `C1.FORMULAS.v0.1`, 18 formulas.
- Active upstream observation authority remains the OPT-A v2 role selector set.
- Validation remains `LOCKED_UNCONSUMED`.

## Implemented packet

- strict OPT-A-v2-shaped input adapter;
- immutable typed source and result models;
- registry-aligned Decimal formula engine;
- immediate contiguous-prior-close resolver;
- deterministic record identity and canonical serializer;
- local result validator;
- golden, boundary, gap, side, control-clock, legacy-parent, Validation-lock and rerun tests.

## Findings

The engine produces deterministic arithmetic facts from approved synthetic inputs. Zero range, unavailable tick size and unlawful prior-close dependencies remain explicit nulls. A gap is never bridged, another side is never substituted, H1 controls are rejected, historical OPT-A v1 is rejected and locked Validation cannot be consumed.

Synthetic outputs retain `authority_state=NONE`; machine path, runtime and wall-clock data do not participate in identity.

## Authority delta

WP3 authorises preparation of WP4 candidate replay and local-release work only after a separate exact operator approval naming the approved OPT-A v2 role release, clocks, sides, interval and external workspace.

Still denied:

- any market replay under WP3 authority;
- local release freeze without WP4 QA and inventory review;
- R2 publication or selector activation;
- Validation consumption;
- C2 consumption;
- probability, exposure, trading or execution.

## Rollback

Rollback removes WP3 implementation approval and returns C1 to the frozen WP2 design. It does not alter OPT-A selectors or any immutable remote object.

## Next gate

`C1-G0 — WP3 reference-engine review and WP4 replay-scope approval`
