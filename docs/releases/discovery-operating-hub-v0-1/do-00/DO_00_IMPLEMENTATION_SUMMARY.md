# DO-00 — Discovery Operating Hub v0.3 realignment

Status: `COMPLETE — RC-A0 / RC-G0A COORDINATION REQUIRED BEFORE DO-G0`

## Decision

Realign OVC Discovery Operating Hub v0.1 to **OVC Research Console v0.3 — Unified Operations Workspaces**.

The earlier decision to implement through the v0.2 fourteen-route architecture is superseded. The fourteen v0.2 destinations are now mapped into three contextual workspaces:

- `OVERVIEW`
- `RESEARCH`
- `SYSTEM`

The v0.2 authority, health-truth, explicit-empty-state, cutoff, deterministic-read-model, local-only and no-mutation constraints remain inherited.

## Structural ownership

Research Console v0.3 owns the shell and interaction architecture: icon rail, workspace switching, context bar, detail drawer, command palette, persistent activity stream and session-state mechanics.

Discovery Operating Hub owns programme-specific projections and operating content: discovery status, prospective research context, neutral recurrence inventory, research-friction ledger, attention queues and architecture-promotion packets.

Research Operations Foundation remains the owner of append-only record creation, audit, artifact catalogue, QA and typed source records.

No duplicate shell, second route system or console-side record writer is authorised.

## Workspace placement

### Overview

- programme authority and represented build context;
- ambient multidomain health;
- release, gate, object, session and incident summaries;
- attention conditions and recent source-derived activity.

### Research

- instrument, release, side, clock, time and cutoff context;
- research brief and uncertainty;
- prospective/review replay with hard cutoff separation;
- evidence and claim lineage;
- read-only session timeline and queue;
- neutral recurrence and discovery-friction views.

### System

- governed objects and lineage;
- artifact catalogue;
- releases, selectors, QA and gates;
- configuration, programme contracts and review packets;
- persistent source-derived activity.

## Context model

Workspace switching and drawer/search/activity interactions preserve compatible instrument, release, clock, side, timestamp, cutoff, mode and filters. Session state is presentation-only and excluded from logical authority.

Search uses approved indexed fields only. Drawer detail opens in place and exposes IDs, hashes, lineage, consequence and next valid action. Activity excludes ordinary page-view events.

## Authority retained

DO-00 grants `DESIGN_RECORDS_ONLY`.

No provider request, market payload, R2 mutation, selector change, threshold change, release action, direct repository write, market classification, semantic promotion, probability, exposure, trading, execution, agent action or remote deployment is authorised.

Console-originated research writes remain deferred to RC-WP7 or another separately approved action plan. Existing CLI/service writes remain governed by the Research Operations Foundation.

C2E, C2.5, C3, OPT-C and OPT-D remain deferred. Validation remains `LOCKED_UNCONSUMED`.

## Baseline

- Repository: `owenguobadia24s-collab/ovc-replay`
- Main baseline: `f704f33e4d5fc19f5807d0a92156b99afa8bce84`
- Research Operations Foundation: `ACTIVE_RESEARCH_OPERATIONS_LOCAL`
- C1 Discovery: `ACTIVE_DISCOVERY`
- C1 Development: `ACTIVE_DEVELOPMENT`
- C1 Validation: `NONE / LOCKED_UNCONSUMED`
- C2: `WP1 boundary frozen / selector NONE`

## Gate sequence

1. `RC-A0 — v0.3 information-architecture amendment`
2. `RC-G0A — v0.3 contract acceptance`
3. `DO-G0 — Discovery Operating Hub operational readiness`

DO-G0 must verify exact v0.3 registries, typed workspace projections, health truth, cutoff safety, lineage, empty states and the absence of a console mutation path before authorising DO-WP1.
