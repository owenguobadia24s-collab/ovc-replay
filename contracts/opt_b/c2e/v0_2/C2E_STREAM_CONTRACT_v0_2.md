# C2E Stream Contract v0.2

The semantic C2E stream is append-only. It consists of immutable EpisodeGenesis, MembershipDelta, BoundaryEvent and LineageEdge records plus rebuildable EpisodeSnapshot and PhaseSegment projections. Checkpoints are replaceable operational artifacts and have no semantic authority.

Episode identity is created only from genesis-available source/release/scope/scale/side/boundary-pack/birth evidence. Eventual members, end time, final status, terminal boundary, later snapshots, family/semantic labels and outcomes are forbidden from genesis identity.

Logical record IDs are SHA-256-derived from canonical identity payloads. Logical hashes cover immutable record content excluding the hash field. Logical stream hashes consume canonical record bytes plus newline in canonical stream order. File path, compression, hostname, worker/PID, wall-clock execution time and presentation order do not enter logical identity.

Base lifecycle states are OPEN, CENSORED, CONFLICTED and TERMINATED. `CENSOR_RELEASE_END` and `CENSOR_GAP` do not imply completion. Under base v0.2 a later release never reopens the same censored identity.

This contract creates no active selector, boundary-pack, source-replay, publication, Validation, semantic, family, probability, risk, exposure or execution authority.
