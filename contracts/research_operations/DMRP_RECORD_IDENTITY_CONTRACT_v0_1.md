# DMRP Research Operations Record & Identity Contract v0.1

Programme: `OVC-EC1-DMRP-CONFORMANCE-v0.1`  
Packet: `DMRPI-WP1`  
Authority effect: **NONE**. This contract authorises no real-source read/write, candidate freeze, Development/Validation access, semantic/family promotion, publication or exposure action.

## Identity planes

The following identities are deliberately non-transitive and MUST remain distinct:

`scientific_object_identity != research_operations_record_identity != irof_semantic_run_identity != physical_attempt_or_artifact_identity`.

A DMRP scientific object is identified from an explicit `scientific_payload` only. `semantic_sha256` is SHA-256 over canonical JSON of `{record_type, scientific_payload}`. Hostname, worker, local path, restart identifier, physical attempt, artifact location, creation time and durable envelope metadata are not scientific identity inputs.

A durable Research Operations record is identified from the complete v0.2 envelope excluding its self-referential `record_id` and `record_sha256`. `record_sha256` therefore changes when durable provenance changes even when `semantic_sha256` is stable.

## Causality and lineage

Effective time and first-valid/admissible knowledge time remain distinct. Frozen records are immutable. Corrections and semantic amendments create new records/generations with explicit `supersedes`/`derived_from` lineage; no helper may mutate a frozen scientific payload in place.

## Canonicalisation

The implementation reuses `ovc.research_operations.canonical.canonical_json_bytes` / `canonical_sha256`, which sort object keys, use compact JSON separators, UTF-8, reject NaN/Infinity and are independent of host/path/worker ordering.

## Backward compatibility

The v0.1 Research Operations schema and records remain unchanged and addressable. v0.2 is additive: it introduces DMRP record families without rewriting any v0.1 bytes or deterministic IDs.

## Authority firewall

Constructing, hashing, freezing, validating or storing a DMRP record has `authority_effect=NONE`. Authority is supplied only by separately governed decision/binding records; this contract may record such references but may not manufacture them.
