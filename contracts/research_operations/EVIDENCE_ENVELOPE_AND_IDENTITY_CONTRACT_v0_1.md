# Evidence Envelope and Identity Contract v0.1

Status: `FROZEN_AFTER_RO_WP1`

Every durable Research Operations record uses one envelope:

- `record_id`, `record_type`, `schema_version`;
- `lifecycle_state`, `created_at`, `frozen_at`, `operator_id`;
- `admissible_cutoff`, `source_release_refs`;
- optional `artifact_refs` and optional `model_refs`;
- `missingness`, `lineage`, `authority_state`;
- `reproducibility_state`, `payload`, `content_sha256`.

`model_refs` is optional. An OPT-A-only observation is valid.

Canonical JSON is UTF-8, keys sorted lexicographically, arrays retained in declared order, no insignificant whitespace, no NaN or Infinity, and one trailing newline for stored bytes.

The deterministic ID is:

```text
ro:<lowercase-record-type>:<sha256-of-frozen-logical-record>
```

Identity material excludes only `record_id` and `content_sha256`. Changed logical content cannot reuse an ID.

No reference whose `first_valid_time` or `available_at` is later than `admissible_cutoff` may enter a prospective record. Such a reference is blocked as `POST_CUTOFF_REFERENCE`.

External evidence availability is explicit:

- all required artifacts verified: `REPRODUCIBLE`;
- some verified and some unavailable: `PARTIALLY_AVAILABLE`;
- no required artifact available: `NOT_REPRODUCIBLE`.

Missing evidence never causes silent record removal.