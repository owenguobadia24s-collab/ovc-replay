# OVC Research Console v0.3 Deferral Decision

Decision: `DEFERRED_NOT_ADOPTED`  
Recorded under: RC-WP1 — OVC Research Console v0.2  
Effective branch: `build/research-console-v0-2-shell-navigation`

## Decision

Continue the accepted OVC Research Console v0.2 programme through RC-WP1. Do not implement or partially introduce the proposed v0.3 unified-workspaces architecture in this work package.

## Reason

RC-G0 accepted the v0.2 information architecture, route registry, card registry, status vocabulary, empty-state rules and action boundary. The v0.3 proposal changes primary navigation, route ownership, contextual state and interaction contracts. Those changes require an explicit amendment preflight and operator gate; they cannot enter RC-WP1 as informal design drift.

## Deferred v0.3 concepts

- three primary workspaces replacing fourteen frozen routes;
- 52 px icon rail replacing the accepted grouped navigation shell;
- universal command palette;
- global contextual right drawer;
- persistent activity stream replacing the dedicated Audit route;
- integrated Research workspace replacing Desk, Replay, Evidence, Sessions and Queue routes;
- ambient health grid replacing Health as a dedicated route.

## Preservation rule

RC-WP1 may use visual qualities shared by both proposals—dark colours, compact context, status badges, cards and progressive disclosure—only where they remain compatible with the accepted v0.2 contracts.

## Re-entry condition

A future v0.3 implementation may begin only after a separately approved amendment package freezes:

1. workspace and panel registries;
2. migration mapping for every v0.2 route and action;
3. session-state and context-preservation contracts;
4. drawer, search and activity authority boundaries;
5. regression evidence that v0.2 safety and health-truth rules remain intact.
