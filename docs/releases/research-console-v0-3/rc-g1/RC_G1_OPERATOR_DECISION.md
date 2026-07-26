# RC-G1-v0.3 — Shell, Context-Preservation and Responsive Acceptance

**Decision: PASS — the OVC Research Console v0.3 shell, context-preservation model and responsive presentation contract are accepted.**

## Accepted implementation

RC-WP1-v0.3 is accepted as a local fixture-only presentation surface. The accepted shell contains exactly three primary workspaces — Overview, Research and System — plus the compact icon rail, workspace tabs, persistent represented-context bar, authority strip, contextual detail drawer, read-only command palette, ambient health and source-derived activity stream.

The Research workspace keeps brief, replay, evidence and queue in one selected context. The System workspace keeps health, lineage, catalogue, releases, QA/gates, audit, configuration and About as sections rather than primary routes.

## Context and safety findings

- Lawful workspace changes preserve the represented repository, source commit, read-model identity, instrument, release, clock, price side, selected time and cutoff mode.
- Drawer selection is presentation state only and cannot edit source records or authority.
- `PROSPECTIVE` mode remains explicitly cutoff-safe; `REVIEW` is separately labelled.
- Research-record health remains `NOT_EVALUATED` with zero progress when no assertion exists.
- Unknown status fails closed to `BLOCK`; status is not communicated by colour alone.
- The command palette searches registered fixture objects only and cannot run mutating commands.
- Responsive acceptance covers the registered 1280, 1440 and 1920 widths, the bounded three-column layout and the narrow-screen CSS fallback at 1100 px.

## Authority delta

RC-WP2-v0.3 may implement deterministic Overview and ambient-health projections against approved Research Operations sources. Those projections may not become active console authority until RC-G2 passes.

The accepted shell remains fixture-only. Live Research surfaces remain denied pending RC-G3. Research writes remain denied pending a separate gate. Repository, selector, threshold, release, market, probability, exposure, execution and agent authority remain `NONE`. Remote deployment remains denied.

## Verification basis

- PR #61 reviewed head: `4f2450ded381945a088d1f0b21c0a2745c172577`
- RC-WP1 merge commit: `fa210386378db684419fe6a38b89870dbf72de2d`
- Canonical tests run: `30202230348` — PASS
- Dedicated RC-WP1 workflow: `30202230381` — PASS
- Blocking issues: `0`

## Disposition

`RC_G1_PASS_RC_WP2_V0_3_AUTHORISED`

Next workstream: `RC-WP2-v0.3 — Overview workspace and ambient health`.
