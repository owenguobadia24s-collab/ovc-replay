# OVC SRFDI-G8R Backend Admission Contract v0.2

Status: G8R implementation contract after operator PASS at `SRFDI-G8R-G0`.

## Authority

This contract governs compute-backend admission only. It grants no representation, normalization, distance, family, sensitivity, selector, publication, Validation, probability, risk, exposure, trading, execution, WP9 or June benchmark authority.

## Reference oracle

`CURRENT_JSON_REFERENCE` — the accepted Python/Decimal SRFD implementation on the frozen scientific semantics — remains normative logical correctness and fallback.

## Allowed backend states

- `REFERENCE_ORACLE`: Python/Decimal reference path.
- `BASELINE_OPTIMIZED`: Python standard-library compute-only equivalent implementation.
- `CANDIDATE_UNADMITTED`: may be imported only for admission tests, never consumed by benchmark execution.
- `ADMITTED_EXACT`: backend has complete exact equivalence, overflow, determinism and dependency identity receipts.
- `QUARANTINED`: backend failed equivalence, determinism, corruption or dependency rules and cannot satisfy a downstream dependency.

## NumPy candidate rules

NumPy is `CANDIDATE_UNADMITTED` until a `BACKEND_ADMISSION_RECEIPT` records PASS.

1. No floating-point arithmetic in equivalence-critical distance or family paths without a separately governed exactness proof.
2. Fixed-width integer dtypes require proven coefficient and intermediate overflow bounds. Overflow fails closed.
3. If a portable exact dtype cannot represent required values, use a structured/two-limb or stdlib exact fallback; never silently downcast.
4. Endianness and memory layout are explicit physical metadata. Logical identity is reconstructed independently of those details.
5. No random state, ordering dependence or hidden multithreading may alter deterministic scientific order or ties.
6. Dependency identity records exact package version/build/platform metadata for capacity reproducibility while scientific logical identity remains backend-neutral after equivalence.

## Admission evidence

A `BACKEND_ADMISSION_RECEIPT` must bind:

- dependency name/version/build/platform;
- backend semantic version and code commit;
- exactness constraints and dtype/overflow policy;
- complete fixture manifest hashes;
- reference and candidate logical hashes;
- pair reconstruction, distance, radius, family, parallel and restart equivalence where the backend participates;
- deterministic worker/order/path evidence;
- decision `ADMITTED_EXACT`, `DEFERRED`, `BLOCKED` or `QUARANTINED`.

Admission is compute-only and never constitutes scientific method preference.

## Science / compute firewall

Every change must be classified as exactly one of:

- `COMPUTE_ONLY_EQUIVALENT`
- `PHYSICAL_STORAGE_ONLY`
- `ORCHESTRATION_ONLY`
- `OBSERVABILITY_ONLY`
- `DEPENDENCY_CHANGE`
- `POTENTIAL_SEMANTIC_CHANGE`

`POTENTIAL_SEMANTIC_CHANGE` is blocking and exits G8R immediately.

## Rollback

Disable or quarantine the candidate backend, preserve its evidence, and revert to the last admitted exact backend without changing the frozen scientific contract.
