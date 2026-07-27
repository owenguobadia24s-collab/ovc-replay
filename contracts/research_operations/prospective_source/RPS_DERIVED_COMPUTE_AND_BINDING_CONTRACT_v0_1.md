# RPS Derived Compute and Exact Source Binding Contract v0.1

## Authority

This contract implements `RPS-WP3` after delegated `RPS-G2` acceptance of the exact local source slice:

- `RPS.DUKASCOPY.GBPUSD.20260622_20260625.v1`;
- manifest logical SHA-256 `429b7b568b7a43d04893c1873773f0b1b567730f2d5d4122d6a1c06dd40e3e41`;
- coverage state `GAPPED`;
- interval `[2026-06-22T00:00:00Z, 2026-06-25T00:00:00Z)`.

The packet is deterministic, local, derived and non-activating. It creates no release, selector, R2 publication, Validation consumption, LIVE_PROSPECTIVE append or ACTIVE_RESEARCH_TRIAGE authority.

## Exact input

The command accepts only the frozen slice under `OVC_EXTERNAL_ARTIFACT_ROOT`. Before compute it must verify:

1. the repository compact-evidence index;
2. all nine local compact evidence files by byte size and SHA-256;
3. the source manifest file and canonical logical hashes;
4. all four source-object identities, metadata, sizes and SHA-256 values;
5. the exact M1 BID and ASK row counts and boundaries.

Native H1 remains a reconciliation control and is not substituted for M1-derived 15M or 2H parents.

## Coverage law

M1 is aggregated only into UTC-aligned complete parents:

- 15M requires exactly 15 unique contiguous M1 rows;
- `2H_A_L` requires exactly 120 unique contiguous M1 rows;
- the admissible cutoff is `2026-06-25T00:00:00Z`;
- any incomplete parent is emitted only as `QUARANTINED_INCOMPLETE_PARENT_SET` and cannot enter C1 or C2.

Expected per side:

| Clock | Total parents | Complete | Unavailable |
|---|---:|---:|---:|
| 15M | 288 | 271 | 17 |
| 2H_A_L | 36 | 30 | 6 |

No repair, forward fill, interpolation, zero-volume fabrication or synthesis is permitted.

## Prospective C1 profile

The exact C1 formula registry `C1.FORMULAS.v0.1` is reused without formula change. The added input profile is selected only by `operation_mode: TIME_GATED_REPLAY` and requires:

- non-release price-set and source-manifest identities in the `RPS.*` namespace;
- Discovery research role;
- selector state `NONE`;
- authority `TIME_GATED_REPLAY_DERIVED`;
- Validation consumption `DENIED`;
- release membership `false`;
- complete 15M or 2H parent;
- first-valid time equal to the parent close.

Historical OPT-A release adaptation remains unchanged. Prospective records cannot claim an OPT-A release or active OPT-A selector.

## Prospective C2 profile

The actual deterministic C2 structure, state, persistence and transition engine is reused with the existing active Discovery model identity:

`OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v1`.

The added handoff profile requires exact RPS C1-set, C1-manifest, price-set, source-manifest and price-bar identities. It requires `TIME_GATED_REPLAY_DERIVED`, release membership `false`, selector eligibility `NONE`, and R2, Validation and LIVE_PROSPECTIVE states `DENIED`.

The engine evaluates:

- 2H local scope;
- 15M local scope;
- 15M with latest first-valid 2H parent levels.

Source gaps reset C1 prior continuity and C2 history, persistence and transitions. Gaps are never bridged.

## Compute run and binding

Every successful execution records:

- exact repository code commit;
- source slice and manifest hash;
- operation mode and admissible cutoff;
- deterministic payload inventory and output-manifest hash;
- deterministic `RPS.RUN.*` compute-run identity;
- deterministic `RPS.BINDING.*` replay-binding identity;
- complete lineage and GAPPED exclusion QA;
- explicit non-release and non-activating authority states.

The binding status is only `ACCEPTED_FOR_REPLAY_CANDIDATE`. It cannot activate research triage or grant write authority.

## Storage and execution

Outputs stay under the external artifact root. Execution is denied in CI and performs no network access. The repository contains contracts, schemas, tests, command code, QA and compact receipts only.

## Failure

Any identity, byte, chronology, coverage, parent, formula, handoff, authority or output-size failure blocks completion and moves only the new compute staging workspace to a separate local quarantine. The frozen source slice and original source quarantines remain unchanged.

## Retained prohibitions

Provider requests, source mutation, gap repair, incomplete-parent consumption, release creation, selector mutation, R2 publication, Validation consumption, LIVE_PROSPECTIVE append, ACTIVE_RESEARCH_TRIAGE, semantic or theory promotion, probability, risk, exposure, trading, execution and agent write remain denied.
