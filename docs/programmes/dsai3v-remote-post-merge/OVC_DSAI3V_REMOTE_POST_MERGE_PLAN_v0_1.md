# OVC DSAI3V Remote Post-Merge Completion Migration v0.1

Programme ID: `OVC-DSAI3V-REMOTE-POST-MERGE-0001`  
Parent programme: `OVC-DSAI-VIT-v0.3`  
Baseline: `main@3fc5aa1cd51da59976a4a43a7d390474969b5c9c` / tree `3980d955b7e5d4e677902ea33e489afa83e307e3`  
Operator direction: 4 September 2026 — replace the self-hosted completion dependency so ordinary OVC development does not require an operator-owned computer to be online.  
Authority delta at G0: bounded implementation only.  
Reserved gate: `DSAI3V-REMOTE-G-CUTOVER-R2`.

## Decision

Move the VIT post-merge completion executor from the operator's self-hosted Windows machine to a GitHub-hosted runner while preserving the existing physical-main controller, SIQ gateway, exact pre-write freeze recovery, exact tree equality proof, content-addressed receipt identities, no-force-push rule and no scientific/semantic/exposure authority.

The migration separates **receipt construction** from **receipt persistence**:

1. a GitHub-hosted runner reconstructs the exact already-effective physical transaction;
2. it generates the canonical completion bundle into an isolated runner-local staging directory;
3. it verifies the same receipt identities and exact-tree proof as the existing local executor;
4. an immutable remote publisher mirrors the staged receipt tree into a dedicated development-receipt namespace;
5. every remote object is read back byte-for-byte and SHA-256 verified;
6. an already-present identical object is accepted idempotently; a conflicting object at the same key fails closed;
7. the local `OVC_EXTERNAL_ARTIFACT_ROOT/receipts` store becomes an optional mirror/recovery surface, never a prerequisite for ordinary GitHub completion.

## Constitutional rule

**Operator devices are clients, not required infrastructure.**

Phone, laptop, desktop and agent-originated repository work must all be able to complete ordinary GitHub integration without requiring an operator-owned machine to remain online.

## Work packets

### REMOTE-WP0 — authority/source reconciliation

- bind current main and existing DSAI3V VIT general authority;
- preserve `DSAI_VIT_PHYSICAL_CONTROLLER` and `DSAI_SIQ_EXISTING_SERIALIZED_GATEWAY`;
- preserve existing pre-write freeze and late-binding recovery semantics;
- record the operator's migration direction;
- classify R2 publication/cutover as separately reserved.

### REMOTE-WP1 — deterministic cloud-neutral staging

- add an explicit receipt-store-root injection to the late-binding completion CLI;
- keep `ReceiptStore` and receipt construction semantics unchanged;
- run canonical completion generation in a GitHub runner temporary directory;
- add tests proving no local external-root dependency is required when an explicit staging root is supplied.

### REMOTE-WP2 — immutable remote publisher

- add a deterministic publisher for a content-addressed receipt directory;
- prohibit deletion, overwrite, path traversal and symlink publication;
- accept only byte-identical pre-existing remote objects;
- verify every newly uploaded or pre-existing object by remote readback and SHA-256;
- produce a compact publication report.

### REMOTE-WP3 — workflow cutover candidate

- change `.github/workflows/vit-post-merge-completion.yml` from `[self-hosted, Windows]` to `ubuntu-latest`;
- install Python package plus `rclone`;
- stage receipts under `${RUNNER_TEMP}`;
- publish only to the dedicated non-release prefix `ovc-evidence/development/vit-completion-receipts/v1`;
- retain read-only GitHub permissions; no Git/main write capability is added;
- upload a diagnostic workflow artifact after remote verification.

### DSAI3V-REMOTE-G-CUTOVER-R2 — OPERATOR REQUIRED

The candidate must stop before merge because the first automatic R2 receipt write is a reserved external publication action. PASS authorises only the dedicated development-receipt namespace and the replacement of the self-hosted executor. It does **not** authorise canonical release publication, selector/model/semantic activation, Validation, probability/risk/exposure/trading/execution, force-push, history rewrite or a new physical-main writer.

## Acceptance conditions

- repository tests pass on the exact PR head;
- workflow contract tests prove `ubuntu-latest` and absence of `self-hosted`/`OVC_EXTERNAL_ARTIFACT_ROOT` as runtime prerequisites;
- publisher tests prove idempotent identical replay, collision failure, path/symlink rejection and readback verification;
- existing completion runtime tests remain green;
- current VIT/SIQ/GRT integration assurance remains unchanged;
- no unresolved review or warning remains;
- cutover PR head is pinned before operator decision and merge.

## Rollback

Forward-revert the workflow to the prior self-hosted executor and preserve all locally or remotely emitted receipt objects. Do not delete or rewrite either receipt history or Git history. The physical-main controller/gateway and all pre-write evidence remain unchanged throughout rollback.
