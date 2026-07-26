# RO-G3 — Research Operations Foundation acceptance and local-console activation review

## Decision

**PASS**

Reviewed Research Operations Foundation v0.1 at merged RO-WP3 commit `2e7b7fd31ad87eeb14d545e9b667a53a6f98337d`.

The deterministic no-mutation QA runner, replaceable typed read model, multidimensional health projection, source-lineage surfaces, local static console, optional Streamlit shell, deterministic build script and localhost Windows launcher are accepted for bounded local operation.

## Evidence reviewed

- RO-WP3 pull request: `#35`
- PR-head commit: `613b61bcaf9b8ad073a11d5424c1395798f8e563`
- merged RO-WP3 commit: `2e7b7fd31ad87eeb14d545e9b667a53a6f98337d`
- canonical workflow run: `30189873318` — success
- canonical command: `PYTHONPATH=src python3 -m unittest discover -s tests -v`
- candidate packet: `docs/releases/research-operations-foundation/ro-wp3/RO_G3_CANDIDATE_GATE_PACKET.json`
- accepted packet: `docs/releases/research-operations-foundation/ro-g3/RO_G3_GATE_PACKET.json`

## Acceptance findings

- QA execution preserves target bytes and propagates blocking results without silent repair.
- Repeated read-model builds from the same compact logical inputs produce the same logical hash.
- Indexed objects retain portable source references and lineage.
- Missing, stale, quarantined, blocking and not-evaluable states remain visible.
- The console consumes only the derived typed read model and exposes no direct write control.
- Governed research writes remain available only through the approved RO-WP2 append-only service and CLI.
- The local read-model database can be discarded and rebuilt without losing authority.
- Validation remains metadata-only and `LOCKED_UNCONSUMED`.

## Authority delta

Approved:

- local QA assurance operation;
- replaceable local derived read-model operation;
- local read-only console operation on `127.0.0.1`;
- continued bounded RO-WP2 append-only research operations.

Not approved:

- provider access or market release creation;
- R2 publication or mutation;
- selector, threshold, parameter or classification mutation;
- Validation payload consumption;
- probability, exposure, trading or execution;
- autonomous agent authority;
- direct UI writes to Git or the primary branch.

## Foundation state

`OVC-RESEARCH-OPERATIONS-FOUNDATION.v0.1` is accepted as `ACTIVE_RESEARCH_OPERATIONS_LOCAL` with **no market or exposure authority**.

## Rollback

Disable the local console and delete the derived `var/research_operations/read_model` state. Preserve all compact records, contracts, catalogues, QA packets and audit evidence. RO-WP2 governed services remain independently reversible under their existing controls.

Operator: Owen Vitae  
Decision date: 26 July 2026
