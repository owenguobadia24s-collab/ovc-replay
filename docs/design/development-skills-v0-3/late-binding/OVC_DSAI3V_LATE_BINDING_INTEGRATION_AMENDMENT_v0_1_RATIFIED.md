# DSAI v0.3 / VIT Late-Binding Integration Amendment v0.1 — RATIFIED

Decision: `PASS`  
Operator instruction: 2026-08-19 — “can you integrate this DSAI/VIT late-binding integration redesign” following the explicit Rules A–D discussion.  
Parent design: `OVC-DSAI-CONTINUOUS-EXECUTION-VIT-DESIGN-SPEC-0.3` / DSAI3-D1…D310.  
Parent implementation programme: `OVC-DSAI-VIT-v0.3`.  
Repository-effective amendment packet: `DSAI3V-LB-WP1`.  
Authority effect: bounded development/integration-semantics amendment only.

## Defect being corrected

The implemented VIT route retained an exact placement predecessor tree and train ordinal on a PR before the PR owned the physical-main integration slot. The physical gateway then waited for the open placement that produced that predecessor. This fixed PR-number ordering but preserved a carriage/train blockage: an unrelated slow or failed candidate earlier in the speculative train could delay otherwise qualified candidates, while physical-main movement forced placement renewal and replacement/reconciliation work even when the PIP was unchanged.

That behavior contradicts the parent design's intended separation of construction from integration and its requirement that normal predecessor materialisation not create global stale-main invalidation.

## Forward amendment

The forward integration model is:

`parallel development -> stable PIP -> base-independent assurance -> qualified payload pool -> dependency/conflict runnable frontier -> one physical writer lease -> late VIT placement against actual main -> exact-final assurance -> physical materialisation -> receipts -> frontier reevaluation`.

The following rules are normative:

1. **No early main binding.** PIP and base-independent assurance are physical-main independent. A candidate is not born with a durable current-main predecessor.
2. **No absolute queue position.** PR number, arrival order, and historical VIT ordinal are non-blocking scheduling hints only. True dependencies/conflicts remain hard constraints.
3. **Late VIT placement.** VIT creates the physical placement only after the candidate owns the final one-writer lease and has resolved the actual current main.
4. **Impact-scoped invalidation.** Irrelevant main movement discards only an ephemeral placement. It does not create a new payload, PR, branch, or full assurance generation.
5. **One physical writer remains.** This amendment does not authorize parallel physical merges. It minimizes the serialized region instead.

## Supersession map

Preserved:
- physical `main` is the sole operational court record;
- one VIT physical integration controller / serialized physical gateway;
- immutable content-addressed PIP identity;
- exact Git tree identity and GRT proof;
- authority/security firewalls;
- append-only historical generations and receipts;
- no force-push/history rewrite.

Prospectively superseded:
- decision-bearing early `predecessor_tree` binding on newly qualified PRs;
- train ordinal as a blocking live-integration relation;
- waiting for an unresolved VIT placement solely because it was provisionally ahead;
- requirement that a qualified PR head already contain the current physical main before it can remain qualified;
- full/base-independent assurance renewal solely because unrelated main advanced;
- replacement PR/commit generation solely to refresh placement.

Historical v1 lineage remains valid evidence and is not rewritten. During migration, v1 placement fields are accepted as provenance but are non-authoritative for live qualification/order.

## Acceptance conditions

The amendment is conformant only if tests prove:
- an earlier unready independent candidate cannot block a later runnable candidate;
- a declared real dependency still blocks;
- payload-only lineage carries no physical predecessor/placement;
- main movement with unchanged PIP/frontiers is placement-only and preserves base-independent assurance;
- live admission contains no train-predecessor polling/wait path;
- exact-final assurance runs on a prospective tree late-bound to the actual acquired main;
- physical main remains one-writer protected and exact-tree/GRT fail-closed;
- no workflow gains GitHub contents/pull-request write or merge authority from this packet.

## Operator-reserved boundaries preserved

No scientific/semantic/selector/model/family/candidate/theory promotion, no new research authority, no Validation, publication, probability/risk/exposure/trading/execution, no parallel physical writer, no destructive action, no force-push/history rewrite, and no general agent-write authority are created by this amendment.
