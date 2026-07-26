# OVC Research Console v0.3 Information-Architecture Contract

Document ID: `OVC-RESEARCH-CONSOLE-INFORMATION-ARCHITECTURE-CONTRACT.v0.3`  
Status: `ACCEPTED_BY_RC_A1`  
Supersedes implementation direction: `OVC-RESEARCH-CONSOLE-V0.2-IMPLEMENTATION-PLAN-0.1`

## Purpose

Freeze the unified-workspaces information architecture before any v0.3 shell implementation begins.

## Active workspace set

| Workspace | Primary question | Authority |
|---|---|---|
| `OVERVIEW` | What system and research context is represented, what is due, and what is blocked? | Derived read-only |
| `RESEARCH` | What is the selected market or research object doing, what supports it, what contradicts it, and what changes it? | Read-only and cutoff-safe when materialized |
| `SYSTEM` | Which releases, sources, QA assertions, lineage and configuration references produce the represented state? | Read-only operational inspection |

No fourth primary workspace may be introduced without a new contract version.

## Global shell contract

The shell contains:

- a compact workspace rail;
- three workspace tabs;
- a persistent represented-context header;
- a context bar for market/release selection;
- an optional contextual detail drawer;
- an ambient health projection;
- a source-derived activity stream;
- an optional read-only command palette.

The shell must continuously display `LOCAL`, represented source commit, read-model identity and current authority mode.

## Context contract

Global context fields are versioned and explicit:

`repository`, `branch`, `source_commit`, `read_model_sha256`, `instrument`, `release_role`, `release_id`, `clock`, `price_side`, `selected_time`, `cutoff_mode`, `selected_object_id`, `freshness`.

Workspace navigation preserves lawful global context. A field may become `NOT_APPLICABLE`; it may not be silently cleared, replaced or inferred from a different release.

## Research cutoff law

`PROSPECTIVE` mode denies post-cutoff evidence to all research panels and forms. `REVIEW` mode may expose later evidence only in a separately labelled region carrying its own source references and first-valid time.

## Global-surface authority

- The contextual drawer may inspect registered source, lineage, status, consequence and next-action fields only.
- The activity stream is a projection of immutable audit, gate, release, QA and research events. It cannot create or edit events.
- The command palette may navigate, search, filter, open source detail and copy identifiers. It cannot invoke unregistered or mutating actions.
- Ambient health remains multidimensional. No aggregate colour or score may conceal domain status or consequence.

## Inherited v0.2 safeguards

The v0.2 status vocabulary, empty-state truth rules and active read-only action meanings remain normative until replaced by a separately reviewed v0.3 version. In particular:

- `no_signal_is_pass: false`;
- unknown status falls back to `BLOCK`;
- empty surfaces state reason, consequence and next valid action;
- colour-only status is forbidden;
- unregistered actions are prohibited;
- the Deploy control remains replaced by a non-clickable `LOCAL` treatment.

## RC-A1 implementation authority

RC-A1 authorises fixture-only local presentation of the shared shell, three workspaces, context surfaces, contextual drawer shell, command-palette shell, ambient-health shell and activity-stream shell. Fixture rendering may demonstrate `VALID`, `EMPTY`, `WARN`, `BLOCK`, `NOT_EVALUATED`, `STALE` and `NOT_MATERIALIZED` states.

Live read-model projections, live Research workspace data and governed research writes remain separately gated.

## Prohibited authority

The v0.3 information architecture creates no authority for repository mutation, research-record creation, selector mutation, threshold mutation, release activation, market classification, probability, exposure, trading, execution, agents or remote deployment.

## Supersession and preservation

The v0.2 implementation plan and pending RC-WP1 direction are superseded. Existing v0.2 contracts, registries, decisions and code branches remain historical evidence. Reuse is permitted only through the v0.3 migration registry and a later implementation gate.

## Change control

Changing workspace ownership, context persistence, drawer authority, activity semantics, command-palette actions, cutoff treatment or inherited safety rules requires a new contract version and operator gate.