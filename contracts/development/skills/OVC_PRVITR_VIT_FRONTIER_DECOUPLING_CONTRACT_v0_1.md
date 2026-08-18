# OVC PRVITR/VIT Frontier Decoupling Contract v0.1

Authority: deterministic conformance correction under the already-active bounded DSAI3V general VIT authority. Authority delta is `NONE`. This contract grants no new scientific, publication, provider-intake, validation, risk, exposure, execution, agent-write, force-push, history-rewrite or parallel-merge authority.

## Purpose

This contract removes the remaining physical-`main` ancestry coupling from PRVITR readiness. A permanent pull request is transport and source provenance for one semantic packet. The immutable `PacketIntegrationPayload` (`PIP`) is the packet identity. A lawful change to the physical materialisation frontier recomposes that same PIP into a new VIT generation and placement; it does not require a replacement branch, replacement PR or reconstruction of unchanged packet work.

## Normative identity separation

The following identities are distinct and MUST NOT be collapsed:

1. `source_head` — the observed pull-request commit/tree, PR number and head ref. It proves the source payload transported by the PR. It is provenance only and is excluded from PIP, VIT generation and placement identity.
2. `PIP` — the content-addressed logical mutation, authority manifest, dependency frontier and prepared completion transition. It is immutable across ordinary frontier movement.
3. `VIT placement` — one deterministic application of the PIP to an exact predecessor tree, producing one `prospective_result_tree`. A new lawful predecessor creates a new generation/placement while preserving the PIP.
4. `prospective_result_tree` — the exact Git tree qualified for materialisation. It need not equal the source PR head tree after lawful frontier movement.
5. `PhysicalMaterialisationTransaction` — the late, exclusive transaction binding the exact predecessor commit/tree, exact VIT generation/placement, exact prospective result tree and exact authority/assurance frontiers.

One semantic packet SHOULD retain one permanent PR. Main movement alone MUST NOT create a replacement PR.

## A0/A1/A2/A3 partition

- **A0 — PIP assurance.** Repository/payload assurance binds the immutable PIP and source provenance. Unrelated physical-main movement does not invalidate A0.
- **A1 — deterministic composition.** A1 proves `predecessor tree + PIP -> prospective result tree` using the registered reference apply profile. A new placement renews A1.
- **A2 — exact prospective-tree assurance.** GRT and other genuinely base-sensitive checks bind the exact VIT generation, placement and prospective result tree. A2 runs inside the late physical lane after the predecessor is frozen.
- **A3 — physical equivalence.** After the squash materialisation, A3 proves `physical main tree == prospective result tree` and emits the `PhysicalMaterialisationReceipt` and `PacketCompletionReceipt` path.

A0 evidence may be reused only when PIP, dependency and authority identities remain unchanged. A1/A2 evidence may never be silently reused across a placement change. A3 may never pass on tree inequality.

## Frontier movement dispositions

- `NO_MOVEMENT` — current predecessor tree is already the source predecessor.
- `PLACEMENT_RECOMPUTE_ONLY` — unrelated lawful movement; preserve PR, source head, PIP and A0; create a new VIT generation/placement and renew A1/A2.
- `ASSURANCE_RENEWAL_REQUIRED` — the integration harness changed without changing packet premise; preserve PR/PIP/A0 and renew affected integration assurance plus A1/A2.
- `PAYLOAD_REBUILD_REQUIRED` — payload path, consumed dependency or identity binding changed; fail closed and require a new PIP only if the packet premise is lawfully repaired.
- `AUTHORITY_REVIEW_REQUIRED` — authority or semantic-authority surface changed; fail closed at the appropriate authority boundary.
- `WAITING_VIT_PREDECESSOR` — the exact encoded VIT predecessor is not yet physical; wait on that placement only. Unrelated PR order cannot create a predecessor lease.

`PLACEMENT_RECOMPUTE_ONLY` is the default for lawful, unrelated physical-main movement. It MUST be attempted before any payload rebuild or packet reconstruction.

## PRVITR readiness rule

PRVITR readiness MUST NOT require current physical `main` to be an ancestor of `source_head`.

Readiness requires:

- the live PR source head still equals the observed source head;
- the source PIP exactly reproduces the source PR tree from its recorded source predecessor;
- the source predecessor is either physical/historical or has one exact VIT placement predecessor;
- current-frontier recomposition is deterministic and non-conflicting;
- A0 is PASS for the immutable PIP;
- A1 identifies the exact prospective result tree.

The source PR head remains the workflow transport key. The prospective commit/tree is the A2 execution target.

## Late physical-main rule

The single physical integration lane freezes `(predecessor commit, predecessor tree, VIT generation, placement, prospective result tree, authority frontier, assurance frontier)` only after A0/A1 readiness. If physical main changes before or during A2, the transaction MUST abort with `PREDECESSOR_MOVED` and the same PIP MUST be recomposed. That event does not authorize a fresh branch, replacement PR, force-push or history rewrite.

The one-writer invariant remains absolute. `parallel_merge` remains `false`.

## Result-tree and post-write equality

The decision-bearing pre-write assertion is:

`VIT prospective_result_tree == qualified prospective materialisation tree`

It is not:

`VIT result_tree == source PR head tree`

The decision-bearing post-write assertion is:

`physical_main_tree == VIT prospective_result_tree`

Any mismatch emits `POST_WRITE_TREE_MISMATCH` and blocks completion.

## Frontier ledger and receipts

The late transaction freeze carries one closed `frontier_ledger_envelope` containing canonical encoded records for:

- the frontier VIT lineage;
- the final A2-qualified assurance generation;
- the exact A2 prospective-tree proof.

Post-merge A3 MUST decode, revalidate and persist each record separately in the content-addressed `ReceiptStore`, then persist the envelope. Administrative closeout PRs are not ordinary integration contestants.

## Regression requirements

The implementation MUST prove at least:

- unrelated main movement preserves PIP, PR and source-head identity;
- the same movement creates a new placement and renews only A1/A2;
- no replacement branch or PR is required;
- integration-harness movement preserves A0 but renews affected assurance;
- payload, dependency, semantic and authority changes still fail closed;
- unrelated earlier PRs cannot hold the physical predecessor lease;
- main movement after lease acquisition emits `PREDECESSOR_MOVED`;
- the final physical tree must equal the qualified prospective result tree exactly;
- A3 persists the frontier lineage, assurance, A2 proof and receipt bundle without a second closeout PR.

## Rollback

Rollback is a normal revert of the bounded squash merge followed by exact required assurance. Force-push, history rewrite, deletion of historical evidence and silent restoration of stale-main branch churn are prohibited.
