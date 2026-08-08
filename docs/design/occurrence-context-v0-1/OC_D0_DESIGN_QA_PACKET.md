# OC-D0 — Design QA Packet

**Design:** `OVC-OCCURRENCE-CONTEXT-DESIGN-SPEC-0.1`  
**Gate:** `OC-D0`  
**QA scope:** design/source/repository conformance only  
**Latest lawful main reconciled:** `a35543c0845f1af70d896a449bd9739af753b8f4`  
**Authority effect:** `NONE`

## QA disposition

**Recommendation: PASS FOR OPERATOR DESIGN REVIEW**, subject to final-head repository CI and merge-readiness remaining green. This QA does not approve OC-D0 and does not grant implementation authority.

## Assertions

| ID | Assertion | Result |
|---|---|---|
| `OC-DQA-01` | OccurrenceContext is defined as linked contextual metadata, not C2/C2E structural identity. | PASS |
| `OC-DQA-02` | `occurrence_key` depends only on immutable structural-anchor identity; contextual values cannot rewrite that key. | PASS |
| `OC-DQA-03` | Context enrichment is append-only and forward-superseding; earlier structural/context records remain addressable. | PASS |
| `OC-DQA-04` | First-valid chronology uses the max of anchor, populated dependencies, required registry availability/effectivity and own confirmation time. | PASS |
| `OC-DQA-05` | Session/date/era/clock-position and market-condition context are stratifiers/filters/display by default, not hidden representation inputs. | PASS |
| `OC-DQA-06` | `REPRESENTATION_INPUT` is denied globally and requires a separately versioned RepresentationPack admission plus its own benchmark/governance path. | PASS |
| `OC-DQA-07` | MCARB integration uses typed ID/hash/version/admission references or tightly allowlisted descriptors; arbitrary mutable vectors are forbidden. | PASS |
| `OC-DQA-08` | Episode-relative duration/count/phase context requires lawful C2E evidence and preserves censoring-versus-completion semantics. | PASS |
| `OC-DQA-09` | Current C2E court record is correctly reconciled as G6 operator-DEFERRED with real-source replay and activation denied. | PASS |
| `OC-DQA-10` | SFC remains deferred and the standalone OC design does not require SFC implementation authority. | PASS |
| `OC-DQA-11` | Validation occurrence-level access remains denied; schema-level `VALIDATION_METADATA_ONLY` does not grant data access. | PASS |
| `OC-DQA-12` | Future C2P base identity is explicitly context-independent; this design does not start C2P. | PASS |
| `OC-DQA-13` | C2.5/C3 consumers must declare exact field-level context dependencies rather than inherit the envelope implicitly. | PASS |
| `OC-DQA-14` | New instrument/market/side/clock/lattice, scientific MCARB activation, selector/publication, semantic/family promotion and exposure authority remain operator-reserved. | PASS |
| `OC-DQA-15` | Proposed fixtures and implementation QA include deterministic rebuild, hash invariance, missingness, chronology, role leakage and C2P identity negative tests. | PASS |
| `OC-DQA-16` | The PR diff is bounded to OC-D0 design artifacts after latest-main reconciliation; no C2E or other programme files are changed by the candidate diff. | PASS |

## Source/conformance basis

The QA used the accepted market-translation architectural separation, the design-resolution OccurrenceContext contract, MCARB context/reference doctrine, current C2E v0.2 stream/model contracts, SFC deferred state and latest main authority records. It did not infer new session boundaries, market-condition semantics, MCARB promotion status or C2P identity rules beyond the accepted non-contamination boundary.

## Known unresolved items — non-blocking for design acceptance

1. Exact first implementation `CalendarSessionRegistry` artifact and A-L mapping binding.
2. Exact non-activating `authority_state` enum names for the implementation contract.
3. Which MCARB record classes, if any, receive initial explicit context-reference admission.
4. Compact provider/source descriptor allowlist.
5. Later SFC reopening sequence, if any.
6. Any future C2E real-source G6 supersession/activation path.
7. Any future market-condition vocabulary.

These are explicitly deferred; none is silently defaulted by the design.

## Final-head assurance requirement

Before the operator decides OC-D0, the candidate PR head must have:

- complete repository suite: `SUCCESS`;
- OVC profile assurance / FINAL_HEAD: `SUCCESS`;
- compatibility / merge readiness: `SUCCESS`;
- no unresolved blocking review thread.

Exact workflow IDs are external PR-head evidence and need not be baked into this immutable design QA file; the OC-D0 operator decision must bind the final reviewed head SHA and successful checks.

## Rollback

Close/defer/quarantine PR #448. Main and all runtime/scientific authority remain unchanged.
