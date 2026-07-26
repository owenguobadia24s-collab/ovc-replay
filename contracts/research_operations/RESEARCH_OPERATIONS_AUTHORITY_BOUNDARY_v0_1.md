# Research Operations Authority Boundary v0.1

Status: `FROZEN_AFTER_RO_WP1`

Research Operations is an additive evidence and operating layer inside `ovc-replay`. It may preserve, validate, relate and present approved upstream records. It is not another market Option and cannot rewrite OPT-A, OPT-B or historical records.

RO-WP1 authorises contracts, schemas, deterministic identities, canonical serialization, pure validators, lifecycle rules and synthetic fixtures only.

It does not authorise live operator sessions, durable writes, a CLI, artifact catalogue, QA runner, read model, console, Validation payload access, provider access, R2 mutation, selector or threshold mutation, model classification, probability, exposure, trading, execution or agents.

A record may reference approved OPT-A metadata and separately approved C1/C2 metadata. Every reference retains exact release, manifest, record, schema, contract, commit and first-valid identities. Validation metadata may be visible, but `OPT-A.GBPUSD.VALIDATION.2025.v2` remains `LOCKED_UNCONSUMED`.

Dependency direction is one way:

```text
approved OPT-A and optional approved C1/C2
  -> Research Operations records
  -> QA and gate packets
  -> read model
  -> console
```

Git may store compact contracts, schemas, registries, fixtures, tests, decisions and validated compact records. Raw market data, large evidence, databases, caches and machine-specific paths remain outside Git.

RO-WP2 remains blocked until an explicit `RO-G1 — Evidence integrity` PASS.