# OVC OPT-B Complete-Replay Input Repair Record

**Affected saved bundle:** `OVC_OPT_B_COMPLETE_REPLAY_2026_H1_v0_1.zip`  
**Affected artifact:** `term_records_15m.jsonl.gz`  
**Repair date:** `2026-07-19`  
**Classification:** `PACKAGING/TRANSFER DEFECT — CANONICAL RECOMPUTATION UNCHANGED`

## Detected defect

The retrieved ZIP container passed ZIP CRC testing, but its embedded 15M term
stream ended before the gzip end-of-stream marker. The embedded artifact had
SHA-256:

`b7042144956c4f908bdee842562cce7114d9670f776e63337bbd6b4e632296b7`

This did not match the complete-replay manifest declaration:

`25505fbc050de39fec384ad8fdf1158842ce020f28dff838997ae6b18d778259`

## Deterministic recovery

The 15M replay was regenerated using the sealed `OPT-A.GBPUSD.2026H1.v1`
canonical bars, the same `B-REF-0.1` registry, `B-LANG-0.1-SEED` parameters,
and the unchanged v0.3 engine's complete-replay implementation.

Recovered result:

- records: `2,624,005`;
- compressed artifact SHA-256:
  `25505fbc050de39fec384ad8fdf1158842ce020f28dff838997ae6b18d778259`;
- canonical JSONL SHA-256:
  `f76a1beabbb37af519ea81fe5da3faaf08e757da16fe7fca9904ad461825545e`.

Both hashes exactly match the original complete-replay manifest. The repair
therefore restores declared bytes; it does not revise any term, threshold,
count, semantic decision or authority boundary.

The corrupted saved archive must remain historical evidence of the transfer
defect and must not be used as a replay source. A separately named repaired
bundle preserves the original manifest with the restored artifact.

