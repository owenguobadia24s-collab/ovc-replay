# C2P ObjectAssertion Genesis Contract v0.2
Status: FROZEN_INACTIVE_CONFORMANCE / authority_effect=NONE

Genesis requires one exact ObjectPack, immutable genesis evidence IDs, an exact genesis MatchDecision and lawful confirmation.
`object_assertion_id = SHA256(canonical({hash_version, object_pack_id, structural_role_id, geometry_kind_id, hard_scope, immutable_genesis_evidence_ids, genesis_match_decision_id, first_valid_identity_time}))`.
Identity excludes later members, snapshots, lifecycle terminal time, family/context annotations, UI labels and downstream semantics.
