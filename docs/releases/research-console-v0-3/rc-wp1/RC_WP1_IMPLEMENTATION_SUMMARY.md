# RC-WP1-v0.3 — Design system, unified shell and navigation

Status: `COMPLETE_RC_G1_V0_3_REVIEW_READY`

## Result

The raw single-page Research Console entry point is replaced by the accepted v0.3 fixture-only shell.

The shell implements exactly three primary workspaces:

- `Overview` — represented context, authority, release/gate summary, queue summary, ambient health and activity;
- `Research` — persistent instrument/release/clock/cutoff context, research brief, replay strip, evidence rail and ambient queue;
- `System` — health, lineage, catalogue, releases, QA/gates, audit, configuration and About sections.

## Global surfaces

- compact icon rail and workspace tabs;
- persistent represented source commit and read-model identity;
- non-clickable `LOCAL · NO DEPLOY` treatment;
- compact and expandable authority boundary;
- read-only fixture command palette;
- contextual detail drawer with lineage and source references;
- ambient multidimensional health in every workspace;
- persistent source-derived activity stream.

## Truth and safety

The shell provides `VALID`, `EMPTY`, `WARN` and `BLOCK` fixture conditions. Empty health does not imply PASS. Research-record health is explicitly `NOT_EVALUATED` with zero progress because RC-WP1 has no live record assertions.

`PROSPECTIVE` mode explicitly denies post-cutoff evidence. `REVIEW` is a separate labelled presentation mode. This work package does not consume live market, research, release, QA or artifact projections; the existing read model contributes represented identity only.

## Authority

Granted: `FIXTURE_ONLY_LOCAL_PRESENTATION`.

Denied: live projections, live Research data, research writes, repository mutation, selector or threshold mutation, release activation, market classification, probability, exposure, execution, agents and remote deployment.

## Baseline

The implementation branch was rebuilt from current main `ea4d4dac2ec07845b82250980207c99e98eb581b` so parallel OPT-B.C2 work is preserved. RC-A1 authority originates at `f93a84e9bfdf36b28ba79f84da8163c3ae4e3b10`.

## Next gate

`RC-G1-v0.3 — shell, context-preservation and responsive acceptance`.
