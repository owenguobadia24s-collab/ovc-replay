# OVC Project Source Archive — 2026-08-12

Historical reference only. Not authoritative for current runtime behavior.

## Purpose

This archive prevents ChatGPT Project source-capacity pruning from deleting OVC design history. The 13 source documents selected for Project-source removal are retained as exact external artifacts, while this repository directory carries their immutable identities, SHA-256 hashes, storage receipts, authority status and removal-safety rule.

The archive is additive and non-destructive. It grants no implementation, selector, semantic, family, publication, Validation, probability, risk, exposure, trading, execution, agent-write or governance-write authority.

## Storage model

OVC already separates bulky/external artifacts from the Git court record. Accordingly:

- exact DOCX/PDF source bytes are stored in the private Google Drive folder identified in `SOURCE_ARCHIVE_MANIFEST.json`;
- Git stores the archive manifest, exact source SHA-256 values, file sizes, external file IDs, disposition and verification evidence;
- historical source files MUST NOT be imported by runtime code merely because they are retained here.

## Removal safety rule

**Do not remove any of these 13 documents from ChatGPT Project Sources until this archive record is merged to `main`.**

After merge, a source is eligible for Project-context removal only when its manifest entry remains `VERIFIED_SOURCE_UPLOAD_SIZE_MATCH` and its external artifact receipt is still addressable. Removing a Project Source changes only ChatGPT context capacity; it does not supersede or delete the historical document.

## Verification performed

1. Re-resolved repository `main` at `3a79d4e28be8663c8201023ba7bd5a3b9353634d`.
2. Confirmed related references/receipts exist in the repository but the 13 exact standalone source binaries were not present as a complete archive on baseline `main`.
3. Computed SHA-256 and byte size from each source file before archival.
4. Uploaded all 13 exact source files to the dedicated external archive folder using their original source file references and MIME types.
5. Re-listed the archive folder and confirmed all 13 filenames and byte sizes match the source inventory.
6. Materialised this Git archive record on an isolated documentation branch.

A post-upload redownload-and-rehash was not performed by the connector; the manifest therefore records the stronger evidence actually obtained rather than claiming an unperformed check.

## Files

- `SOURCE_ARCHIVE_MANIFEST.json` — machine-readable source identities, hashes, external receipts and disposition.
- `REMOVAL_CHECKLIST.md` — operator-facing removal eligibility checklist.

## Rollback

Before merge: close the archive PR and keep all Project Sources loaded. After merge: retaining or re-adding any Project Source is always allowed; the archive does not require removal.
