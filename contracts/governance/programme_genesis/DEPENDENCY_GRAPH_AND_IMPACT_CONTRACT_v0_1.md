# Dependency Graph and Impact Contract v0.1

## Packet and authority

- Programme: `OVC-PG-v0.2`
- Packet / gate: `PG-WP3` / `PG-G3`
- Authority: typed dependency representation, deterministic validation and derived impact analysis only

This contract grants no existing-programme migration, graph-based authority, admission enforcement, Control Plane route, automatic upkeep, market/model authority, selector or release mutation, Validation, publication, agent write, probability, risk, exposure, trading or execution authority. `PG-G3A` remains a mandatory operator acknowledgement before `PG-WP4` migration.

## Node contract

Every node has:

- stable `node_id`;
- registered `node_type`;
- title and lifecycle status;
- optional `programme_id`;
- authority classification that is descriptive only;
- source references with precedence and authority role;
- partition identity;
- explicit provisional or accepted status.

Unknown node types, duplicate IDs, missing source references and orphan identities fail closed.

## Edge contract

Every edge has:

- stable `edge_id`;
- existing `from_node` and `to_node`;
- an edge type from `EDGE_TYPE_REGISTRY_v0_1`;
- lawful hardness for that type;
- `SOURCE_EXPLICIT` or `ADAPTER_INFERRED` source kind;
- one or more exact source references;
- `authority_effect = NONE`;
- acceptance status.

Direction follows the frozen registry. For dependency edges, `from_node` is dependent and `to_node` is prerequisite. `PARENT_OF` is the explicit exception and runs parent to child.

## Hard prerequisite rule

A hard prerequisite is valid only when:

1. its type permits `HARD`;
2. the registry marks the type as source-explicit for hard use;
3. `source_kind` is `SOURCE_EXPLICIT`;
4. the source record supports the exact edge;
5. no accepted hard dependency cycle results.

An inferred edge may inform review but cannot satisfy a hard gate, establish completion, create parentage or convey authority.

## Cycle policy

- any hard dependency cycle is `QUARANTINE`;
- self-edges are `BLOCK`;
- cycles composed only of soft or informational edges are `WARN` and remain visible;
- no cycle is silently broken by dropping an edge;
- graph validation reports the canonical cycle path.

## Authority path policy

- every edge carries `authority_effect = NONE`;
- no path from code, tests, QA, PRs, commits, graph position or implementation status may terminate as an authority grant;
- accepted authority exists only in an authoritative operator decision or accepted delegated decision whose own authority source is valid;
- the graph may display authority lineage but cannot create, amplify or transfer it;
- a non-`NONE` graph edge effect is `QUARANTINE`.

## Impact analysis

Impact analysis is deterministic and read-only:

- upstream prerequisites are traversed in edge direction;
- downstream impacted nodes are traversed against edge direction;
- results include direct and transitive effects;
- unknown changed nodes fail closed;
- impact output always declares `authority_effect = NONE_DERIVED_ANALYSIS_ONLY`;
- any proposed authority change requires an operator decision outside the graph service.

## Partition and scale controls

Graphs may be partitioned by programme class or constitutional parent. Cross-partition validation requires:

- globally unique node and edge IDs;
- no orphan endpoints;
- no hidden hard cycle across partitions;
- identical edge semantics across partitions;
- no authority inheritance from partition membership;
- deterministic logical graph hashes.

## PG-G3A acknowledgement packet

Before migration, the operator receives one consolidated packet containing:

- graph node/edge census;
- edge-type distribution;
- hard, soft and informational edge distribution;
- all hard cycles and non-hard cycles;
- inferred hard-edge attempts;
- authority-path violations;
- orphan and duplicate findings;
- representative impact analyses;
- explicit migration boundary and rollback.

The allowed acknowledgement decisions are `ACKNOWLEDGE_CONTINUE`, `DEFER`, `BLOCK`, `QUARANTINE` or `SUPERSEDE`. Only `ACKNOWLEDGE_CONTINUE` may release `PG-WP4`, and it grants migration work authority only, not acceptance of imported programme facts.

## Rollback

Discard and rebuild graph projections from accepted source records and edge registries. Preserve all source records, graph snapshots, findings, decisions, PRs and commits. Never rewrite programme-owned state or accepted authority.
