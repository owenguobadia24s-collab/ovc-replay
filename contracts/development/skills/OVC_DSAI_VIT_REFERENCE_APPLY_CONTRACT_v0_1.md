# OVC DSAI v0.3 VIT Reference Apply & External-Main Signal Contract v0.1

Authority: prospective/shadow implementation only. This contract grants no physical-main control.

## Reference apply
The reference apply profile is `INTEGRATION_APPLY_PROFILE_REFERENCE_v0_1`. It consumes one exact predecessor Git tree plus one immutable `PacketIntegrationPayload` and returns exactly one `CompositionReceipt` containing either an exact result Git tree or typed failures.

Allowed mutation operations are `ADD`, `MODIFY`, and `DELETE`. Identity-bearing file content is supplied by exact Git blob SHA and exact Git mode. Absolute paths, parent traversal and `.git` mutation are forbidden. Duplicate mutations of one path are `CONTENT_CONFLICT`. Invalid predecessor, operation, path, mode or object binding is `INPUT_PRECONDITION_MISMATCH`.

A no-op payload that produces the exact predecessor tree remains a valid deterministic composition and is classified downstream as `NO_REPOSITORY_DELTA`; it never requires a meaningless physical merge.

`TreeContentDiagnosticFingerprint` is SHA-256 over the raw sorted `git ls-tree -r -z` representation. It is diagnostic only and never substitutes for exact Git tree identity.

## External-main signals
`AuthorizedExternalMainAdvanceReceipt` is a durable signal that a non-VIT main writer advanced the physical frontier lawfully. Validation requires:
- exactly one active writer identity in `AuthorizedMainWriterRegistry`;
- operation class allowed by that writer;
- exact authority source admitted for that writer;
- exact predecessor commit and tree equal to the observed frontier;
- non-empty result commit/tree and integrity binding.

A valid receipt classifies as `EXTERNAL_MAIN_REANCHOR`; any missing, unknown, stale, conflicting or otherwise unbound signal classifies as `REPOSITORY_INTEGRITY_INCIDENT` and cannot authorize physical landing.

## Non-authority
A receipt explains a sanctioned physical advance; it does not grant future write authority. The VIT physical controller remains inactive until `DSAI3V-G-VIT-PILOT` operator PASS. Parallel physical merge remains forbidden.
