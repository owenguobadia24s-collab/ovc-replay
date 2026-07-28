# RO3-G3 Blocker Decision

## Decision

**BLOCK** — RO3-G3 cannot ratify independent C1 formula assurance.

The packet was executed under the operator-ratified `OVC-RESEARCH-OPERATIONS-FOUNDATION-v0.3-C1-FACT-ASSURANCE-IMPLEMENTATION-PLAN-0.2`. Its proposed authority delta was only `QA_EVIDENCE_ONLY`. No additional authority is granted.

## Exact finding

The frozen formula registry defines `C1-WICK-BALANCE.v0.1` as:

```text
upper_wick_share - lower_wick_share
```

The current C1 implementation computes:

```text
(lower - upper) / range
```

For the exact hand-verifiable fixture, the independent contract oracle produced `-0.1428571428571428571428571429`; the implementation produced `0.1428571428571428571428571429`. This is a deterministic sign inversion.

Blocking assertion: `ro3-c1-golden-assertion:264901109b282f8444f8c41de05d2810d16c7114eba0dd041784d8e8abb4a8f8`.

## Evidence quality

- The independent invariant registry remained byte-identical to the RO3-G0 frozen blob `568309747bbf4e9d368c704893f4a9d0b8af406b`.
- All 18 primitives were reconciled between the formula and invariant registries.
- All 79 metamorphic assertions passed.
- Seventeen of 18 exact golden formula assertions passed.
- Same input produced identical canonical bytes; canonical input reordering was invariant.
- The deliberately corrupted negative control was detected.
- Five focused metamorphic tests, four independence tests and 70 canonical repository tests passed.
- QA recommendation: `BLOCK`.

## Why RO3 cannot repair it

Correcting `src/ovc/opt_b/c1/formulas.py` would alter output bytes in remotely verified Discovery and Development C1 releases. Those releases contain 212,764 records across 192 files. Existing immutable release identities cannot be reused, and the exact affected-record count has not yet been computed.

Changing the formula registry instead would materially change a frozen contract. Either action is outside RO3-WP3 authority. RO3 also cannot rewrite or retire the active C2 selector or any Pattern Discovery artifact.

## Preserved authority

- C1 formulas, records, releases and selectors: unchanged.
- C2 ACTIVE_DISCOVERY authority: unchanged.
- Validation: `LOCKED_UNCONSUMED`.
- RO3-WP4: blocked.
- Live Console C1 presentation: disabled pending RC-G4.
- Probability, risk, exposure, trading, execution and agent authority: none.

## Smallest lawful resolution

Ratify a separate bounded C1 wick-balance implementation reconciliation and immutable release correction plan. It must:

1. Freeze exact current registry, implementation and release hashes.
2. Compute the affected C1 record/file inventory.
3. Trace exact C2 and Pattern Discovery downstream surfaces without mutation.
4. Correct the implementation to the frozen formula registry under a new implementation identity.
5. Replay and QA Discovery and Development under new immutable release identities.
6. Present separate publication, selector-replacement and downstream-remediation gates.
7. Resume RO3-WP3 only after the corrected release chain is remotely verified.

## Continuation point

`RO3-WP3_RETEST_AFTER_C1_CORRECTIVE_PROGRAMME`.
