# SRFDI-WP10 v0.7 Runner Remediation Packet

Status: `IMPLEMENTATION_CANDIDATE_PENDING_EXACT_HEAD_ASSURANCE_AND_MERGE`

The operator has approved the missing production runner remediation. Current `main` at construction start is `9d42780d80bffe2326130d9c2f1fce357d249500`. The current v0.7 token `SRFD.JUNE.AUTH.baad8aa9752b789cea06f41c3bc134e86711a257f1219d04b4034a664a8f1ef5` remains **AUTHORIZED_UNCONSUMED and DO_NOT_START_DURING_REMEDIATION**.

The candidate adds a split production runtime: `wp10_durable_execution.py`, `wp10_v07_contract.py`, `wp10_v07_family.py`, `wp10_v07_analysis.py`, and the orchestration entrypoint `wp10_v07_runner.py`. The durable layer binds atomic output artifacts to checkpoint receipts and verifies them on resume. The contract runtime binds the frozen source/population/registry identities; the family runtime exposes exact reusable domain preparation plus one-configuration materialization; the analysis runtime implements the frozen v0.4 evidence calculations with capacity-safe semantics; and the runner performs exact preflight before token consumption, reconstructs the frozen 9,420-row source and 8,598 eligible population from six accepted files, compiles the unchanged 36 comparability domains, checkpoints domain preparation separately, checkpoints every one of the 1,944 frozen family configurations individually, executes the two frozen segmentation methods, and materializes the frozen v0.4 sensitivity, correspondence, ambiguity, chronology, invariant-core-support and method-disagreement evidence without scientific disposition.

The runner intentionally does **not** import `wp10a_real_capacity.py`, because that module still has an unconditional Unix `resource` import. The runner reuses the same lower-level frozen representation, distance and family primitives while providing a Windows-portable standard-library peak-RSS implementation. Equivalence tests require the new per-configuration materialization route to match `materialize_pattern_full_grid` exactly on an independent fixture, and the capacity-safe invariant/method-disagreement implementations to match the frozen reference semantics.

Candidate implementation binding (construction base):

`db7314c2a6ea31c1d188f84c89ee7c61c7b552c8d66d8f9442a69d7f9cd7f6ba`

Candidate Git blob identities:

- `wp10_execution_resilience.py`: `073772c33f39afc63d8194d34e798aa3dbc9b61b` (existing merged primitive)
- `wp10_durable_execution.py`: `f1afc8b23a229aacf15da8f0d53fda70b46ae1c9`
- `wp10_v07_contract.py`: `1a140e544cfd7d74a90c980198eb1abe0186e1ec`
- `wp10_v07_family.py`: `10dafed0caf15bb941efa8a81cbdeedf44bbec2b`
- `wp10_v07_analysis.py`: `4dd3e64b1041031e49cb81ddffe012e642f42b28`
- `wp10_v07_runner.py`: `47fbf10aeb7ba41ee91cd8638650522401fad82a`

The binding above is candidate engineering identity only. A fresh June run binding must additionally bind the exact post-merge `main` and may be minted only after final assurance.

## Required assurance

- durable artifact survives interruption and committed units are skipped;
- orphan artifact written before checkpoint is idempotently recovered;
- artifact corruption fails closed;
- external artifact quota fails before commit;
- exact 54 configurations per domain and 1,944 family configuration work units overall;
- split per-configuration materialization equals the frozen full-grid reference;
- optimized invariant-core and method-disagreement outputs equal the frozen reference semantics;
- scientific RunBinding drift is rejected before execution;
- a preflight failure leaves no token-consumption receipt;
- full repository suite passes;
- OVC profile, compatibility and merge-readiness pass;
- no unresolved review blocker remains.

## Post-merge disposition

Do not consume the old v0.7 token. Record it as `SUPERSEDED_UNUSED_UNCONSUMED`, construct a fresh exact runner-bound token under the already-merged remaining-sequence delegation, and continue automatically only if every frozen prerequisite still passes.
