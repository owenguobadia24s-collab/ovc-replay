# OPT-B.C1 v2 WP4 Operator Decision

## Decision

`PASS — DISCOVERY AND DEVELOPMENT REPLAY QA COMPLETE; LOCAL CANDIDATE RECORDED`

## Exact execution

- Workflow run: `30185680001`
- Execution commit: `2e2d84ad34fae02992a7861d194c12e0bdbd0c1f`
- Candidate artifact: `8626942276`
- Candidate artifact digest: `sha256:fb52ea4f84fa7c1d79c9c524470d6722ab82b09a5ed4d4f0278fda4d330eabfc`
- QA artifact: `8626942405`
- QA artifact digest: `sha256:2dc137ede8ee8ca2625bb11aaf591dc9935e3261481d0a0f35a272f02b1cb49d`

## Parent authority

The replay used only the exact active OPT-A v2 Discovery and Development r2 manifests approved by B1-G0. Validation 2025 was not downloaded or consumed and remains `LOCKED_UNCONSUMED`.

## Result

The deterministic replay produced 212,764 C1 records across 192 compressed candidate files:

| Role | 15M BID | 15M ASK | 2H_A_L BID | 2H_A_L ASK | Total |
|---|---:|---:|---:|---:|---:|
| Discovery | 71,982 | 71,982 | 7,964 | 7,964 | 159,892 |
| Development | 23,853 | 23,853 | 2,583 | 2,583 | 52,872 |

A second complete replay produced an identical file inventory, byte size and SHA-256 set. Input and output cardinalities matched for every approved role, clock and side.

The replay retained missingness rather than repairing it. It recorded explicit non-contiguous-prior and first-record nulls, excluded 12,104 Discovery and 4,862 Development quarantined upstream records, and performed no cross-side substitution, interpolation or gap repair.

## Lifecycle decision

The workflow artifact is accepted as a **local candidate**, not as a remotely published or selected release. The candidate has `CANDIDATE` authority solely for the next freeze review. Its GitHub Actions retention is finite, so B1-G1 must either freeze it into the approved evidence lifecycle or reject it before expiry.

## Authority retained

- C1 selectors remain `NONE`.
- R2 publication remains denied pending a separate WP5 approval.
- C2 consumption remains denied pending a separate handoff review.
- Validation remains `LOCKED_UNCONSUMED`.
- Probability, exposure, trading and execution authority remain `NONE`.

## Next gate

`OPT-B.C1 v2 B1-G1 — WP4 candidate inventory and freeze review`
