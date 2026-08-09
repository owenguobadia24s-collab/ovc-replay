# GRT-WP0 — Court-Record Preflight

Programme: `OVC-GENESIS-REPOSITORY-TOPOLOGY-v0.1`  
Packet: `GRT-WP0`  
Next gate: `GRT-G0` — **OPERATOR REQUIRED**  
Baseline: `main@1070df70e04bef9541e36461e76e97dfbca6ea20`  
Source instruction SHA-256: `346f0598746b894c9c5cfbba202253505843565c10d41c4aef9c6d87babf7dc4`

## Executive result

`GRT-WP0 = COMPLETE`

The current repository supports the proposed Genesis Repository Topology as an **additive, subordinate derived read model**. No separate topology platform or competing programme authority registry is required.

The strongest reuse path is:

`Programme Genesis graph + Programme Genesis read model + PGN artifact-governance crosswalk + Research Operations ArtifactCatalogue/read model + existing Console shell`

The missing capability is the repository-wide **component-level** scanner/crosswalk/dependency/anomaly/diff layer.

No implementation is authorised before `GRT-G0`.

## Court-record state

- Programme Genesis `OVC-PG-v0.2`: `COMPLETED`; governance canon adopted.
- Programme Genesis portfolio read model: approved only as a derived view subordinate to programme-owned source state.
- Admission enforcement: `DEFERRED_DISABLED`.
- Control Plane route: `DEFERRED_DISABLED_UNREGISTERED`.
- Bounded candidate-event upkeep: active only for authority-neutral append-only candidate persistence.
- Programme creation by Programme Genesis automation: denied.
- PGN native-portfolio programme: `PGN-G3 COMPLETED / DEFER_ALL`; all 16 reviewed candidates remain `CANDIDATE_UNAPPROVED_DEFERRED`; remaining conversion/adoption/enforcement/migration work is indefinitely deferred.
- Research Operations: `ACTIVE_RESEARCH_OPERATIONS_LOCAL`; artifact catalogue and replaceable derived read model are reusable; Console authority remains local/read-only; Validation remains locked unconsumed.

## Existing implementation reuse matrix

| Surface | Disposition | Existing source |
|---|---|---|
| Programme dependency graph / impact | REUSE + EXTEND | `src/ovc/programme_genesis/graph.py` |
| Programme portfolio read model / health | REUSE + EXTEND | `src/ovc/programme_genesis/read_model.py` |
| Artifact nodes / hashing / dependency declarations | REUSE + EXTEND | `src/ovc/research_operations/catalogue.py` |
| Generic Research Operations derived read model | REUSE + EXTEND | `src/ovc/research_operations/read_model.py` |
| Programme-to-artifact evidence classes | REUSE + EXTEND | `OVC_PGN_ARTIFACT_GOVERNANCE_CROSSWALK_CONTRACT_v0_1.md` |
| Control Plane programme projection | REUSE ONLY AFTER NEW OPERATOR GATE | existing disabled `/programmes` adapter candidate |
| Repository-wide component topology scanner | MISSING | build only after `GRT-G0=PASS` |
| Commit-to-commit topology drift/diff | MISSING | build only after `GRT-G0=PASS` |

## Open PR state relevant to topology truth

Current open PRs must remain proposal/evidence state until merged/accepted. In particular:

- `#491` — current C2E signature-contract supersession gate proposal; `GATE_READY`, not accepted.
- `#492` — fresh SRFD run-authority token candidate; not effective until exact-head assurance and merge.
- `#479`, `#433`, `#422`, `#413` — preserved blocker evidence.
- `#418` — draft synthetic fresh-discovery rehearsal, intentionally unmerged/non-promotable.
- `#211` — shadow receipt proposal, do not merge.
- `#202` — older blinded-review construction PR, open/unmerged.

No open PR directly implements the requested Genesis Repository Topology.

## Preflight observations

1. **No duplicate governance system is needed.** The topology can remain subordinate to Programme Genesis.
2. **PGN already provides a useful programme-to-artifact crosswalk precedent.** Its evidence classes should be preserved and extended rather than replaced.
3. **The current Control Plane route is not available.** `PG-G6` explicitly deferred the read-only route and admission enforcement.
4. **One stale-state candidate already exists:** the disabled adapter registry still says `PENDING_PG_G6` although accepted `PG-G6` has already decided `READ_ONLY_ROUTE=DEFER` and `ENFORCEMENT=DEFER`. The actual disabled booleans remain aligned. WP0 records this only; it does not repair it.
5. **Current open PR authority proposals cannot be promoted by topology inference.**
6. **No source or authority mutation is required to implement the requested topology after GRT-G0.**

## Exact GRT scope

In scope after PASS:

- typed component nodes and topology edges;
- deterministic repository scanning;
- programme/component crosswalk projection;
- explicit versus inferred dependency separation;
- anomaly detection;
- deterministic clean rebuild;
- incremental commit-to-commit drift;
- read-only operator projection behind later gate.

Out of scope:

- native programme adoption;
- programme auto-admission/reclassification;
- automatic hard-edge acceptance;
- rewriting Genesis/programme-owned state;
- Control Plane route activation or writes;
- automatic remediation;
- market/model/selector/release/Validation/publication/probability/risk/exposure/execution authority.

## GRT-G0 recommendation

`RECOMMEND PASS`

Rationale: the requested system can be implemented as a deterministic derived read model using existing Programme Genesis and Research Operations primitives without weakening source precedence or creating a second canon.

**STOP:** `GRT-G0` is operator-reserved. No GRT-WP1 design freeze or implementation work may begin until an explicit operator decision is recorded.
