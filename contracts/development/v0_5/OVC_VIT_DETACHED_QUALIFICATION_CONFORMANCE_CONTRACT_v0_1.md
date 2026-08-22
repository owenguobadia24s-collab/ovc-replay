# OVC VIT Detached Qualification Envelope Conformance Contract v0.1

Status: corrective conformance contract under existing `DSAI3V-VIT-GENERAL-AUTHORITY-v0.1`  
Authority effect: `NONE_SAFETY_CONFORMANCE_CORRECTION`

## 1. Purpose

This contract removes decision-bearing PIP, authority-frontier and VIT lineage identity from mutable pull-request text while preserving the active late-physical-placement architecture, current SIQ/GRT assurance, and the single VIT physical-main writer.

It grants no new programme, scientific, semantic, publication, probability, risk, exposure, trading, execution, merge, force-push or history-rewrite authority.

## 2. Separation of identities

OVC MUST treat the following as separate concerns:

1. **Payload truth** — the exact candidate Git head/tree and its canonical `PacketIntegrationPayload`.
2. **Qualification truth** — one immutable qualification envelope binding the exact head/tree to the PIP, authority-manifest identity and dependency-frontier identity used by BASE_INDEPENDENT assurance.
3. **Scheduling state** — a dynamic runnable set; PR number, creation time and an earlier provisional position are not dependency authority.
4. **Physical placement** — an ephemeral VIT binding to the live physical `main`, created only inside the serialized final-integration lease.

Physical `main`, predecessor tree, result tree and queue ordinal MUST NOT be included in the detached qualification envelope for a late-binding candidate.

## 3. Detached qualification ledger

Decision-bearing qualification state is stored outside both the payload tree and pull-request body on the dedicated `ovc/vit-qualification-ledger-v1` ref.

The canonical layout is:

- `.ovc/vit-qualifications/envelopes/<qualification_id>.json` — immutable content-addressed qualification envelope.
- `.ovc/vit-qualifications/heads/<candidate_head_sha>.json` — exact-head pointer to the currently active qualification generation.

An envelope binds:

- exact candidate head SHA;
- exact candidate head tree;
- canonical PIP and PIP ID;
- exact authority-manifest ID;
- exact dependency-frontier ID;
- payload-only late-binding VIT lineage; and
- a content-addressed qualification ID.

Envelope bytes MUST be canonical JSON. A file whose bytes do not hash to its embedded qualification identity MUST fail closed.

The head pointer may lawfully advance to a new qualification generation for the **same Git head** when qualification metadata is corrected. The old envelope remains preserved. This is a qualification supersession, not a payload mutation and not a reason to manufacture an empty Git commit.

## 4. Pull-request metadata is non-authoritative

PR title, body, labels, comments and edit history are provenance/human-review surfaces only. They MUST NOT supply or mutate the decision-bearing PIP, authority-manifest ID, dependency-frontier ID or qualification identity used by required assurance.

`VIT-Lineage-B64` and `VIT-Lineage-Blob` remain readable only for explicit historical recovery/migration. Their presence, absence or later edit on a normal permanent candidate cannot grant, replace or modify qualification authority.

A normal PR may display a human-readable qualification ID for traceability, but CI MUST derive the active qualification from the exact head SHA and detached ledger rather than trusting that display text.

## 5. Qualification freeze

Before required BASE_INDEPENDENT assurance begins, the exact candidate head/tree and one detached qualification ID MUST exist and validate.

For one assurance generation:

- candidate head SHA is immutable;
- candidate head tree is immutable;
- qualification ID is immutable;
- PIP ID is immutable;
- authority-manifest ID is immutable; and
- dependency-frontier ID is immutable.

If the exact-head pointer changes while assurance is running, the running generation is superseded and MUST fail closed. A new assurance generation may run against the same Git head and new qualification ID without any tree-changing or empty transport commit.

## 6. Late physical placement remains unchanged

Qualification MUST NOT bind current physical `main`.

After a candidate is qualified and selected from the dynamically runnable set, `DSAI_VIT_PHYSICAL_CONTROLLER` alone acquires the one-writer integration lease, resolves the then-current physical `main`, composes the prospective result tree, runs mandatory BASE_SENSITIVE/SIQ/GRT exact-final assurance, and materialises only if the final base remains stable.

An unrelated main advance before lease acquisition is not a qualification defect and requires no PIP rebuild. A main advance during the lease discards only the ephemeral placement and retries the same qualified payload where current contracts permit.

## 7. Queue ordering

No PR number, PR creation timestamp or detached qualification creation timestamp is an absolute queue position.

Only real dependency/authority edges constrain ordering. If an earlier candidate is not runnable and a later independent candidate is fully qualified, the scheduler may select the runnable candidate while preserving one-at-a-time physical materialisation.

This contract does not weaken semantic predecessor requirements. A packet that genuinely depends on another packet remains blocked by that dependency.

## 8. Producer invariant

The normal permanent-candidate producer sequence is:

`final payload mutation -> freeze exact head/tree -> build PIP from exact Git blob+mode identities -> resolve authority/frontier -> build/validate detached qualification envelope -> publish immutable envelope + exact-head pointer -> expose/retrigger required CI`.

Any later payload mutation invalidates the prior qualification. Any qualification-only correction creates a new qualification envelope/pointer for the same head and does not require a new commit.

## 9. Historical recovery

Historical merged/open generations created before this cutover may explicitly opt into legacy PR-body lineage resolution for recovery only. Legacy resolution is never the forward default and cannot bypass VIT, SIQ, GRT or exact-final checks.

## 10. Rollback

Rollback is forward-only: disable detached-ledger admission for new generations and explicitly re-enable the prior historical lineage reader while preserving every qualification envelope, pointer generation, PIP, assurance result, placement, receipt and Git history. Never force-push or rewrite history.
