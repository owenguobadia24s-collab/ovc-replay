# OVC Research Console v0.3 — Information-Architecture Amendment v0.1

Document ID: `OVC-RESEARCH-CONSOLE-V0.3-IA-AMENDMENT-0.1`  
Programme gates: `RC-A0` preflight; `RC-A1` acceptance  
Status: `ACCEPTED_BY_RC_A1`  
Repository: `owenguobadia24s-collab/ovc-replay`  
Preflight baseline: `main` at `f704f33e4d5fc19f5807d0a92156b99afa8bce84`  
Acceptance integration baseline: `main` at `2a1b22dc248ebe0f0c1b360062e9e6c1402a5b1a`

## Authority notice

This amendment supersedes the OVC Research Console v0.2 Interface Upgrade Implementation Plan as the active console implementation direction. RC-A1 authorises fixture-only implementation of the v0.3 shell and navigation contract. It does not authorise live projections, market interpretation, research-record creation, repository mutation, selector or threshold mutation, release activation, probability, exposure, execution, agents or remote deployment.

The Research Operations Foundation and its read-only local-console authority remain unchanged. Historical v0.2 contracts, registries, gate packets and the closed RC-WP1 branch remain auditable source material; they do not remain active implementation authority.

## Primary decision

Replace the fourteen-route v0.2 application hierarchy with three persistent workspaces:

1. `OVERVIEW` — operating context, authority, releases, gates, queue, ambient health and recent activity.
2. `RESEARCH` — research brief, cutoff-safe replay, evidence comparison, sessions and due work in one selected market context.
3. `SYSTEM` — releases, QA and gates, data catalogue, lineage, configuration, audit detail and implementation metadata.

The application shell is organised around a compact icon rail, workspace tabs, a persistent context bar, an optional contextual detail drawer, an ambient health grid and a source-derived activity stream. A universal command palette is permitted only for registered read-only navigation, search, filtering and identifier-copy actions.

## Why the amendment is required

The accepted v0.2 route model separated related tasks into fourteen first-class destinations. That preserved authority boundaries, but fragmented the operator's selected market context and made research, evidence, queue and system state feel like separate applications. The v0.3 structure keeps the safety rules while consolidating navigation around the operator's actual modes of work.

## Inherited safety law

The following v0.2 rules survive unchanged:

- local-only deployment bound to `127.0.0.1`;
- persistent represented commit and read-model hash;
- every displayed claim resolves to immutable source references;
- no signal, empty data or stale state may imply `PASS`;
- unknown status fails closed to `BLOCK`;
- status may not be communicated by colour alone;
- unregistered actions are prohibited;
- research writes remain deferred to a separate gate;
- repository, selector, threshold, release and market-model mutation remain prohibited;
- probability, exposure, trading, execution and agents remain `NONE`.

## Workspace model

### Overview workspace

The overview is an operating landing surface, not a raw dashboard. It must expose represented source context, current authority, release and gate summaries, queue consequences, ambient health and recent activity. Every summary opens source detail through the contextual drawer or the System workspace.

### Research workspace

The Research workspace preserves one selected context across brief, replay, evidence and queue panels. Prospective mode must physically withhold post-cutoff information. Review mode may expose later evidence only through an unmistakably separated post-cutoff surface. Sessions and research records remain inspection-only until a separate write-authority gate.

### System workspace

The System workspace contains detailed operational surfaces: health, lineage, catalogue, releases, QA and gates, audit, configuration and implementation/about metadata. It may inspect and compare but may not mutate active authority.

## Global surfaces

- **Icon rail:** stable workspace and help navigation; no hidden mutation actions.
- **Workspace tabs:** `Overview`, `Research`, `System`.
- **Context bar:** repository, branch, source commit, release role and ID, instrument, clock, side, selected time, cutoff mode and freshness.
- **Contextual drawer:** source references, lineage, status meaning, consequence and next valid action for the selected object.
- **Ambient health:** multidimensional status embedded in every workspace, with affected surfaces and consequences.
- **Activity stream:** immutable, source-derived event projection replacing Audit as a mandatory top-level route while retaining full audit detail in System.
- **Command palette:** read-only navigation, registered search, filters, source opening and identifier copy only.

## v0.2 migration rule

No v0.2 route disappears without an explicit v0.3 panel or global-surface destination. The migration registry is normative. Historical URLs or route IDs may remain as compatibility aliases, but they may not establish a second active information architecture.

## Context-preservation law

The selected instrument, release, role, clock, side, time, cutoff mode and selected object are application context. Workspace changes preserve that context unless the target surface declares the field not applicable. Workspace-local filters may reset independently. A drawer selection never mutates canonical records or the underlying read model.

## Programme sequence

- `RC-A0` — amendment preflight, supersession, workspace and migration freeze: complete.
- `RC-A1` — operator acceptance of the v0.3 information architecture and authority boundaries: PASS.
- `RC-WP1-v0.3` — design system and unified shell implementation from fixtures only: authorised.
- `RC-G1-v0.3` — shell, context-preservation and responsive acceptance: next gate after RC-WP1.
- Later read-model and live research gates remain separately governed.

## RC-A1 authority delta

RC-A1 grants `FIXTURE_ONLY_LOCAL_PRESENTATION` for the v0.3 shared shell, three-workspace navigation, persistent context display, contextual drawer shell, command-palette shell, ambient-health shell and activity-stream shell. It grants no live data, write, market, release, selector, threshold, probability, exposure, execution, agent or remote-deployment authority.