# OPT-B.C1 v2 WP1 Operator Decision

## Decision

`PASS — CLEAN C1 BOUNDARY APPROVED`

## Reviewed baseline

- Repository: `owenguobadia24s-collab/ovc-replay`
- Baseline: `fb5b2fea2200b05a050aa1f8af51121a1883a4a5`
- Upstream selector set: `SELECTOR.OPT-A.GBPUSD.ROLESET.v1`
- OPT-A state: active Discovery, active Development, Validation identity active but `LOCKED_UNCONSUMED`
- Historical OPT-A v1 and legacy engine: prohibited as active parent, fallback, parameter source or discovery seed

## Approved boundary

OPT-B.C1 v2 is approved as a distinct atomic-fact layer. It may define versioned, deterministic, bar-local measurements from exact sealed OPT-A v2 inputs. It may use only an explicitly defined immediate contiguous prior close where a primitive requires it.

C1 may not inherit rolling state, levels, containers, events, semantics, outcomes, stories, probability or execution meaning. BID and ASK remain separate. Missing data cannot be repaired through another side, clock or provider-native H1 record.

## WP1 outputs

- authority boundary;
- implementation registry;
- namespace map;
- dependency allowlist and denylist;
- deferred-capability register;
- executable boundary tests.

## Authority delta

WP2 contract, formula-registry, schema and null-policy work is authorised.

The following remain denied:

- actual C1 market replay;
- local C1 release freeze;
- R2 publication;
- C1 selector activation;
- C2 consumption;
- Validation access;
- probability, exposure, trading and execution.

## Rollback

Rollback returns C1 to `DESIGN_AND_FIXTURES_ONLY`. It leaves the OPT-A selector set unchanged and cannot reactivate historical OPT-A v1 or legacy OPT-B code.

## Next work packet

`OPT-B.C1 v2 WP2 — contract, formula registry and schemas`
