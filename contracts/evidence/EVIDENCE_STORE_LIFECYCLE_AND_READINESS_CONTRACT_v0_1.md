# Evidence-store Lifecycle and Readiness Contract v0.1

## Scope

This contract governs `OVC_EXTERNAL_ARTIFACT_ROOT` resolution, mutable workspace creation, deterministic workspace inventory, local release freezing, supersession checks, publication approval binding and non-destructive readiness. Existing manifest construction, immutable upload and full-byte remote verification remain authoritative and are extended rather than replaced.

## External-root rules

- Resolve only from process variable `OVC_EXTERNAL_ARTIFACT_ROOT`.
- Require an absolute operator-controlled directory disjoint from the repository.
- Reject repository-contained, repository-parent and symbolic-link paths.
- Never persist the absolute path or credentials in Git.

## Workspace rules

- A workspace ID uses the same safe segment grammar as release IDs.
- `init-workspace` creates `intake/`, `workspace/` and one new workspace only.
- It must not create a release root, invoke a provider, contact R2 or overwrite an existing workspace.
- Workspace inventories contain exact canonical paths, full SHA-256 values and byte sizes.
- Symlinks, unresolved entries, collisions and unsafe paths are blocking.

## Freeze rules

- Freeze requires `qa_state=PASS` and an exact approved workspace inventory.
- Workspace bytes must match the approved inventory at freeze time.
- The target release ID and freeze receipt must not already exist.
- Freeze copies exact bytes into a new `releases/<release-id>/` root and records a deterministic inventory hash in `receipts/freeze/`.
- No overwrite, repair, inferred file or unresolved QA state is permitted.

## Supersession rules

- A new release ID cannot equal or reuse its predecessor ID.
- The predecessor must be registered and have a legal historical/superseded disposition.
- Historical `OPT-A.GBPUSD.2026H1.v1` can never become a publication ID, selector fallback or rollback target.

## Publication approval rules

Before upload, a record conforming to `ovc-opt-a-publication-approval/v0.2` must bind:

- exact release ID;
- exact manifest ID;
- SHA-256 of the complete local manifest file;
- exact source/build commit;
- operator identity and recorded decision time;
- explicit rollback or stop note;
- decision `APPROVE`.

Any mismatch blocks upload before rclone is invoked.

## Readiness rules

Readiness is read-only and returns `READY`, `BLOCKED` or `NOT_EVALUABLE`. It checks release-root safety, exact inventory, local hashes, manifest schema, prohibited files, symlinks, duplicate remote keys, source commit, clean Git worktree, approval binding, optional rclone visibility, exact-key collision state and supplied lock visibility.

Readiness must never call upload, `rclone copyto`, delete or rewrite. Its result always records `side_effects_performed=false`.

Missing remote configuration or unavailable lock visibility is `NOT_EVALUABLE`; it is never converted to PASS. Existing exact remote keys are `BLOCK`.

## Authority boundary

WP2 activates lifecycle infrastructure only. It grants no provider-download, market-release, R2-publication, selector, validation-consumption, model, probability, exposure or execution authority.
