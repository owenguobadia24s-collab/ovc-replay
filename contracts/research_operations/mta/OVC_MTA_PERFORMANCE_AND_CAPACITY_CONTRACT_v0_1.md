# OVC MTA Performance and Capacity Contract v0.1

## Frozen limits

- Maximum expected wall-clock runtime for one packet execution attempt: `14400` seconds.
- Maximum new retained external artifacts per packet: `10737418240` bytes.
- Inputs already pinned by hash do not count as new retained output.
- Default shard hierarchy: `role -> clock -> side -> week`.

## Preflight estimate

Every packet records expected rows, shard count, expected runtime, temporary bytes, retained bytes, compression and checkpoint cadence before execution.

## Streaming and checkpoints

Full streams are processed incrementally. Checkpoints are mandatory at each shard completion and before 75% of either limit. Each checkpoint binds source hashes, registry versions, cursor, completed shards, partial inventory and logical result hash.

## Capacity states

`WITHIN_CONTRACT`, `CAPACITY_WARNING`, `CAPACITY_EXCEEDED`, `CAPACITY_REMEDIATED`.

## CAPACITY_EXCEEDED

Stop before the bound; close files; hash and inventory partial outputs; emit an incident and non-authoritative checkpoint; preserve completed shards; delete only replaceable temporary material; resume using the frozen shard strategy; recombine deterministically; rerun final QA.

The incident does not itself block the programme. Block only if the smallest lawful shard exceeds four hours, required retained evidence cannot fit under 10GB, or deterministic recombination fails.
