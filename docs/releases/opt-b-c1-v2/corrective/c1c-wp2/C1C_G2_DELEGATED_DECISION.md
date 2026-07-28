# C1C-G2 Delegated Decision

- **Decision:** PASS
- **Authority:** delegated non-activating authority under the operator-ratified corrective programme
- **Programme:** `OVC-C1-WICK-BALANCE-CORRECTIVE-PROGRAMME-0.1`
- **Packet:** `C1C-WP2`
- **Baseline:** `1142abd2010b92b33e56bccc23e05ccd8bed1320`
- **Tested candidate:** `f30efb0ef8b72cb2e43ccb242c479932a6ee8387`
- **Workflow:** `30370847916`
- **QA recommendation:** `PASS_C1C_G2_LOCAL_ONLY`

## Finding

The defect was an implementation-path drift, not an active-release byte defect. The active C1 Discovery and Development releases contain the frozen upper-minus-lower wick-balance sign across all 212,764 records and 192 record shards.

The exact audit found:

- active affected records: **0**;
- active affected files: **0**;
- nonzero records that would diverge under the defective library helper: **208,185**;
- zero-balance records: **4,576**;
- null zero-range records: **3**.

## Local immutable candidates

Two complete corrected-implementation candidate identities were frozen locally:

- `OPT-B.C1.GBPUSD.DISCOVERY.2021_2023.v2` — 159,892 records in 144 shards;
- `OPT-B.C1.GBPUSD.DEVELOPMENT.2024.v2` — 52,872 records in 48 shards.

Every candidate record shard is byte-identical to its active v1 counterpart. The new release identity records `C1.IMPLEMENTATION.v0.2`; no historical identity was reused.

## Formula assurance

The frozen independent invariant canon remained byte-identical to RO3-G0. The corrected implementation passed:

- 79 metamorphic assertions;
- 18 independent golden assertions;
- deterministic rerun and canonical-reorder checks;
- deliberately corrupted implementation negative control.

There were zero failed assertions. RO3 formula assurance therefore recommends PASS.

## Downstream impact

There is no C2 semantic correction caused by active C1 bytes. Replacing C1 release identities would nevertheless require deterministic C2 identity replay over 728,344 state and transition records in 24 files.

Canonical Pattern Discovery is unaffected. The entire noncanonical June 2026 pilot namespace `PD.PILOT.GBPUSD.20260622_20260625.v1` must be invalidated and rerun because its prospective compute path executed before the corrected library implementation was merged.

## Authority delta

The accepted delta is limited to local immutable candidates, impact evidence and QA. It grants no R2 publication, selector replacement, C2 mutation, Pattern Discovery canonical append, Validation, probability, risk, exposure, trading or execution authority.

## Rollback

Discard the unpublished candidate workflow artifacts and rebuild from the exact approved parent artifacts. Active v1 C1 releases and active C2 authority remain unchanged.

## Next boundary

Present one consolidated operator decision packet for:

- `C1C-G3` — R2 publication;
- `C1C-G4` — C1 selector replacement;
- `C1C-G5` — downstream C2 and Pilot Discovery remediation.
