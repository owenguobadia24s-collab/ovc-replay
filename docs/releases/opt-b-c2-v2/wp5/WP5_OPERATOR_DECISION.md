# OPT-B.C2 v2 WP5 — Discovery and Development replay

**Decision: BLOCKED — the exact verified C1 release bytes are not available inside the repository or the GitHub execution environment.**

The WP5 replay runner, release guards and deterministic synthetic QA are complete. The canonical C1 releases are remotely verified in R2, but repository policy excludes their record payloads and this execution has no mounted release root or R2 credentials. Therefore no claim of full 2021–2023 Discovery replay, 2024 Development replay, replay QA pass or local candidate release is made.

Required operator action: make the exact C1 Discovery and Development JSONL exports available under a release root containing `discovery/c1_records.jsonl` and `development/c1_records.jsonl`, then run:

```powershell
$env:PYTHONPATH = "src"
python scripts/opt_b/run_c2_wp5_replay.py --release-root <C1_RELEASE_ROOT> --output-root <C2_LOCAL_CANDIDATE_ROOT>
```

Until that receipt is produced and reviewed, the C2 candidate release, publication, selector and activation remain `NONE`. Validation remains `LOCKED_UNCONSUMED`; probability, exposure, trading and execution remain `NONE`.
