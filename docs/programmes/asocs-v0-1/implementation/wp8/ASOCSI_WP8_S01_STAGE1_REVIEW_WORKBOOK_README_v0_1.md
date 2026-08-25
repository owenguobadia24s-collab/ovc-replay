# ASOCSI WP8 — Session 1 — Stage 1 review workbook

Packet: `ASOCSI-WP8-S01-STAGE1-HUMAN-REVIEW-INTERFACE`  
Authority delta: `NONE`

## Human review surface

The completed reviewer workbook is a content-addressed external presentation artifact:

- **Workbook:** `ASOCSI_WP8_S01_STAGE1_REVIEW_WORKBOOK.html`
- **Google Drive ID:** `1_p3aeMBQq8ICIpcBkysJ32v9V7bmWTL3`
- **Google Drive URL:** `https://drive.google.com/file/d/1_p3aeMBQq8ICIpcBkysJ32v9V7bmWTL3/view?usp=drivesdk`
- **SHA-256:** `4c4a2b6cccb8b2d4551ce6365fe82a6d04519f62cb90b61a004d22f3b739e2b4`
- **Bytes:** `485487`

Repository binding:

- `ASOCSI_WP8_S01_STAGE1_REVIEW_WORKBOOK_ARTIFACT_v0_1.json`
- `ASOCSI_WP8_S01_STAGE1_WP7_PROJECTION_MANIFEST_v0_1.json`

The workbook is deliberately not an authoritative machine record. The repository retains content-addressed identity and source bindings while the large reviewer-facing HTML remains in the governed external-artifact surface, consistent with the existing WP7 human-evidence pattern.

## Authoritative machine inputs

These remain unchanged:

- `ASOCSI_WP8_S01_STAGE1_REVEAL_PACKET_v0_1.json` — SHA-256 `5ae775fd5ac9ad5afcecec4f57f3b3fb4fdb5d1d25e2a8d1d9769fde1c52f5c7`
- `ASOCSI_WP8_S01_STAGE1_HUMAN_INPUT_TEMPLATE_v0_1.json` — SHA-256 `607b1d48137b01f3cbb9ea7ae737382fe6ee152497e412fcb725b6ae635b9c9b`
- governing judgement schema: `schemas/research_operations/asocs/asocs_stage1_fidelity_judgement_v0_1.schema.json`

The workbook embeds a deterministic presentation projection of the frozen WP7 Session-1 reviewer material: canonical order, case identity, original WP7 local source-native SVG chart, frozen review status and frozen A0–A8 observations. The projection is bound by `ASOCSI_WP8_S01_STAGE1_WP7_PROJECTION_MANIFEST_v0_1.json`.

## Open and bind Stage 1

Download/open the HTML workbook. It first attempts to load the exact frozen Stage-1 reveal packet and human-input template from the pinned repository baseline `2ab9ed0bc07f54a5ea7a07ae76e605932ad8f771` and verifies both byte hashes.

If automatic loading is unavailable, use **Bind local frozen records…** and choose the two machine files above from a repository checkout. The reviewer does not need to inspect or edit their JSON contents; the workbook verifies their exact hashes before enabling review.

## Review and export

Review Cases 01–25 sequentially. No Stage-1 response is preselected or inferred. The completion tracker is operational only.

Export is enabled only after every required human judgement field is complete. The workbook produces exactly one:

`ASOCSI_WP8_S01_STAGE1_HUMAN_INPUT.json`

The export starts from the exact frozen template and preserves case ID, presentation ordinal, review unit, predecessor blind-record SHA, session/stage identity, reveal-packet SHA, judgement schema and the locked construct-survival prohibition. It changes only permitted human judgement fields.

Case 19 is the frozen `SOURCE_GAP` review unit. Information-gap disposition is evaluated first. Source limitation does not automatically imply semantic failure, and C1 unavailability caused by the source gap is not itself an arithmetic defect. No judgement is preselected.

Stage 2 is not loaded, constructed or exposed.
