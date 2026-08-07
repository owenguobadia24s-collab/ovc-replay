# MG Clock Profile and As-of Alignment Contract v0.1

**Contract ID:** `MG-CLOCK-PROFILE-ALIGNMENT-0.1`  
**Programme:** `OVC-C2E-C2G-C2P-MARKET-GRAMMAR-REMEDIATION-v0.1`  
**Packet:** `MG-WP5`  
**Authority:** inactive, noncanonical `SHADOW_EXPERIMENT` only

MG-WP5 freezes one comparison profile: 15M evaluation with existing `2H_A_L` context. It does not create, replace or activate a clock.

The as-of resolver selects only the latest exact-scope parent whose `first_valid_time <= child_first_valid_time`. Exact scope requires the same release, instrument and side and the profile-declared parent clock. No fallback crosses release, side, instrument or profile. Duplicate exact parent observations at the same as-of timestamp fail closed.

Resolution states are `AVAILABLE`, `STALE`, `UNAVAILABLE` and `NOT_EVALUABLE`. The profile declares a 7,200-second maximum parent age for this shadow comparison. A stale or not-evaluable parent remains explicit and never becomes neutrality. Future parents are ignored and can never satisfy lineage.

Every resolution records child/parent identity, UTC first-valid timestamps, parent age when computable, profile identity, exact reason and authority state. Ledger identity is deterministic and independent of input iteration, machine and path.

Acceptance requires `parent_first_valid_time <= child_first_valid_time` for every available/stale/not-evaluable binding; explicit missing context; fail-closed cross-side/release/profile parentage; valid/invalid parent-child fixtures; order invariance; complete repository and FINAL_HEAD assurance; and zero reserved authority delta.

Rollback removes or supersedes this inactive resolver/profile while preserving child and parent records, clock identities, QA, decisions and negative evidence. It cannot rewrite clock history.
