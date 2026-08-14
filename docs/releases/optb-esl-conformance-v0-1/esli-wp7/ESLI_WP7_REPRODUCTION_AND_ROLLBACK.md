# ESLI-WP7 reproduction and rollback

Baseline: `605d2ce10c361fd05dc5728171e3361a91f3d1f5`
Branch: `build/esli-wp7-organisation-evidence-requeue5-20260813`
Authority delta: `NONE`.

This branch reconstructs only the already-bounded WP7 implementation from latest lawful main. Prior WP7 attempts and their repository evidence remain preserved.

Required assurance: targeted WP7 tests, dependent ESL/SFC tests, complete repository tests, parity checks, FINAL_HEAD profile assurance, and serialized stable-main readiness.

Rollback: forward-supersede WP7-only artifacts while preserving WP0-WP6, prior-attempt evidence, SFC/SOI evidence, and Git history.
