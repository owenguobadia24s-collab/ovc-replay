# Admissible Cutoff and Validation Isolation Policy v0.1

Status: `FROZEN_AFTER_RO_WP1`

A prospective record may use only information whose `first_valid_time` or `available_at` is less than or equal to its `admissible_cutoff`. Source, artifact and model references are checked recursively.

No later path, post-cutoff model output, retrospective semantic label, outcome, story or adjudication may enter an observation or frozen claim.

Validation identity and governance metadata may be represented. Payload locators, bar identities, model inputs and realized paths are prohibited while Validation remains `LOCKED_UNCONSUMED`.

A lawful Validation metadata reference contains:

```text
release_id: OPT-A.GBPUSD.VALIDATION.2025.v2
validation_access_state: LOCKED_UNCONSUMED
payload_access: DENIED
```

Blocking incident codes are:

- `POST_CUTOFF_REFERENCE`;
- `VALIDATION_PAYLOAD_ACCESS_DENIED`;
- `FROZEN_MUTATION`;
- `DUPLICATE_RECORD_ID`;
- `CONTENT_HASH_MISMATCH`;
- `MISSING_REQUIRED_ARTIFACT`;
- `LINEAGE_UNRESOLVED`.