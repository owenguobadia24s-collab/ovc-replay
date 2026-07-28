# RO3 C1 Index Contract v0.1

Status: `ACCEPTED_AT_RO3_G1` after passing gate evidence.

## Inputs

Only the exact remote-verified SHADOW C1 releases are admissible:

- `OPT-B.C1.GBPUSD.DISCOVERY.2021_2023.v1` / `6abd6d1fb74e7f3797e9add2435eaa5e487b612efd2f4b5f4f4c59679820d5d2`
- `OPT-B.C1.GBPUSD.DEVELOPMENT.2024.v1` / `ca83f2d9d948be426f3d80ebc91cc981f92546dfdd07268d71938d618c51f017`
- `C1.FORMULAS.v0.1` with exactly 18 frozen formulas

Every content request declares `DISCOVERY` or `DEVELOPMENT`. Validation is `NOT_BUILT / LOCKED_UNCONSUMED` and denied before path, object, record or timestamp resolution.

## Outputs

- `C1ReleaseIndex`: exact role, release, manifest, lifecycle, selector, coverage, availability, file and record counts.
- `C1PrimitiveIndex`: one frozen metadata record for each of the 18 primitives.
- `C1RecordFamilyIndex`: deterministic family grouping by role, release, clock, side, schema and formula registry.
- `C1CoverageProfile`: source and record reconciliation, null-bearing fields, rejection counts and explicit role totals.
- `C1IndexBenchmark`: declared machine, Python, operating system, corpus shape, wall time, peak memory, throughput and logical hash.
- `C1IncrementalIndexReceipt`: optional deterministic fallback that binds the prior logical hash, exact added source identities and resulting logical hash.

## Identity

Derived IDs and the final logical hash use SHA-256 over canonical JSON with sorted object keys and deterministic list order. Absolute paths, machine name, run time, input order, pagination and process identity are excluded from logical identity.

## Fail-closed rules

Unknown release, manifest, role, clock, side, schema, registry, formula, unit, null rule or authority vocabulary is blocking. Duplicate identities with conflicting content are blocking. Missing source counts or release hashes yield `NOT_EVALUATED`, never implied PASS.

## Performance envelope

The required full-corpus shape is 212,764 C1 records across 192 files. A declared-machine full-corpus build has a 300-second soft target. If it exceeds the target, the only lawful fallback is deterministic incremental indexing with identical final logical hash and explicit source-addition receipt. Unbounded, unreliable or non-reproducible operation blocks RO3-G1.

## Authority

Outputs are replaceable local derived evidence. Writes to C1 source records, releases, selectors, Git primary branch, R2, Validation, C2, Pattern Discovery, formulas, thresholds or semantic objects are prohibited.
