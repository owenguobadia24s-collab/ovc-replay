# OVC DSAI3V Remote Post-Merge Completion Executor Contract v0.1

Programme: `OVC-DSAI3V-REMOTE-POST-MERGE-0001`  
Parent: `OVC-DSAI-VIT-v0.3`  
Status: CUTOVER CANDIDATE / NOT ACTIVE UNTIL `DSAI3V-REMOTE-G-CUTOVER-R2` PASS  
Authority delta before cutover: NONE.

## Purpose

Replace the operator-local/self-hosted Windows completion executor with a GitHub-hosted executor without changing physical-main write authority, VIT/SIQ ordering, exact-tree semantics or completion receipt identity.

## Invariants

- Physical main remains the court record.
- `DSAI_VIT_PHYSICAL_CONTROLLER` remains the physical writer.
- `DSAI_SIQ_EXISTING_SERIALIZED_GATEWAY` remains the physical gateway.
- The executor runs only after main has already advanced.
- The executor has read-only GitHub repository permissions.
- The executor never force-pushes, rewrites history, merges or writes repository content.
- Existing pre-write freeze / late-binding placement evidence remains the sole source for transaction reconstruction.
- The exact physical tree must equal the frozen expected result tree.
- `PhysicalMaterialisationReceipt`, `PacketCompletionReceipt`, canonical DEVOBS receipt and completion-observability attachment retain their existing construction and content-addressed identities.

## Execution model

The executor runs on `ubuntu-latest`. It checks out the already-effective main SHA with full history and creates a temporary staging root beneath `RUNNER_TEMP`. The late-binding completion CLI receives that exact staging root explicitly; it therefore does not require `OVC_EXTERNAL_ARTIFACT_ROOT` or any operator-local filesystem.

After the canonical completion bundle is produced, the remote publisher mirrors the complete staged receipt tree to the dedicated development namespace:

`ovc-evidence/development/vit-completion-receipts/v1/`

The namespace is not a canonical release namespace. Every object is immutable-by-content:

- missing object -> upload once, then read back and verify exact bytes/SHA-256;
- existing byte-identical object -> accept idempotently;
- existing different object at the same key -> fail `REMOTE_RECEIPT_COLLISION`;
- deletion/overwrite is prohibited;
- symlink/path-traversal publication is prohibited.

## Device independence

No operator-owned machine, local path, mounted drive or self-hosted runner may be required for ordinary post-merge completion. Local receipt stores remain valid optional mirrors/recovery surfaces only.

## R2 cutover boundary

The first automatic write to the remote R2 receipt namespace and activation of this executor on main are operator-reserved at `DSAI3V-REMOTE-G-CUTOVER-R2`. Before PASS, implementation/tests/PR preparation are allowed but the candidate must not be merged.

## Failure behaviour

Missing R2 credentials, missing exact pre-write evidence, ambiguous associated PR, tree mismatch, missing required checks, remote collision, readback mismatch or incomplete receipt bundle fails closed. No failure authorises fallback to the Git worktree, a local operator machine, an ephemeral-only completion state or a different cloud namespace.

## Rollback

Forward-revert the workflow to the preceding self-hosted executor while preserving all existing receipt objects and Git history. Rollback never repeats an already-effective physical main write.
