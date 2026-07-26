# OPT-B.C2 v2 WP5 - exact-parent replay readiness

**Decision: BLOCKED only on the missing exact OPT-A Discovery and Development release roots.**

The C1/C2 record-contract mismatch is resolved by C2-G3R. C2 now consumes the immutable published C1 primitive record together with the exact OPT-A source row named by its lineage. C1 is not rewritten or expanded.

The runner now requires both parent roots:

```powershell
$env:PYTHONPATH = "src"
python scripts/opt_b/run_c2_wp5_replay.py `
  --release-root $C1Root `
  --opt-a-release-root $OptARoot `
  --output-root $C2Output `
  --verify-only
```

Verification binds and reads every manifest-declared byte in the two C1 releases and the two OPT-A releases before any source row is joined.

Without `--verify-only`, the engine:

- joins C1 to OPT-A by exact role, release, manifest, manifest hash, source path, timestamp and source-bar ID;
- checks current-bar primitives against exact OHLC;
- derives first-valid rolling ranges, midpoints and confirmed swings;
- emits local 15M, local 2H and 15M-with-latest-first-valid-2H scopes;
- resets history, persistence and transitions at gaps.

Actual Discovery and Development replay remains `NOT_EXECUTED` until the exact OPT-A roots are mounted. Local candidate release, publication, selector and activation remain `NONE`. Validation remains `LOCKED_UNCONSUMED`; probability, exposure, trading and execution remain `NONE`.
