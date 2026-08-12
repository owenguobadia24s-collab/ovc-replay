# C2P ObjectPack Contract v0.2
Status: FROZEN_INACTIVE_CONFORMANCE / authority_effect=NONE

Every identity decision is scoped by one exact immutable ObjectPack identity and pinned `object_pack_hash`.
Changing any identity-defining extraction, role, geometry, scope, Tracklet, confirmation, matching, retrieval-proof, continuity, retirement, split/merge, chronology or serialization semantic creates a different pack identity and cannot reuse an ObjectAssertion ID.

A conformant ObjectPack explicitly freezes: candidate extraction; Tracklet open/update/confirm/expire and ambiguity policy; genesis/confirmation; exact matching predicates; candidate-retrieval superset obligation; continuity/dormancy/retirement; split/merge disposition; bitemporal chronology; canonical serialization; replay/checkpoint operations; and authority/rollback metadata. Retrieval is never identity authority.

WP1 admits only activation-ineligible, real-source-forbidden synthetic packs A/B. `active_object_pack_id` remains null. No empirical or active pack is selected.
