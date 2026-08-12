# C2 → StructuralOccurrence reference adapter v0.1

Packet: `ESLI-WP3`. Authority: inactive deterministic conformance only.

The bootstrap adapter consumes one lawful `c2_observation/vnext-r1` anchor plus the exact four-axis C2 formula-profile outputs available by the evaluation cutoff. It does not read raw price, reconstruct C2, select a family, consume global QUALITY, infer missing profiles, or inspect outcomes/future evidence.

Bootstrap scope is frozen to GBPUSD / BID / 15M / UTC under `OPTB-ESL-OCCURRENCE-PACK-GBPUSD-BID-15M-v0.1`. C2Observation is REQUIRED. C2P, C2E and OccurrenceContext are OPTIONAL and appear only as exact typed dependency refs supplied by the caller.

Each of LOCATION, MOTION, ORGANISATION and INTERACTION is emitted independently. No profile → `MISSING`; profile(s) present but none computable → `NOT_EVALUABLE`; at least one computable component → `AVAILABLE` with exact profile facts and component statuses. Missing/NOT_EVALUABLE never become zero-valued facts.

The output FVT is not earlier than every REQUIRED identity-defining input FVT and never exceeds evaluation cutoff. The compiler validates the complete occurrence with the WP1 invariant runtime, hashes its EvidenceFrontier under canonical-json-v1, then computes `so1:` identity over the exact immutable occurrence payload.
