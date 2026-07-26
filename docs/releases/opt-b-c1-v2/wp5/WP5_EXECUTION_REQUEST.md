# OPT-B.C1 v2 WP5 reconciliation execution request

Execute the idempotent WP5 reconciliation against the exact WP4F Discovery and Development artifacts from workflow run `30187276514`.

Required result:

- accept existing remote objects only when size and SHA-256 exactly match the frozen manifest;
- immutably upload only missing objects;
- preserve payload-first and manifest-last completion semantics;
- stream and verify every remote byte;
- write the WP5 publication packet and remote-verification receipt;
- keep the C1 selector at `NONE`;
- keep C2 consumption denied;
- keep Validation `LOCKED_UNCONSUMED`.
# OPT-B.C1 v2 WP5 execution request

Execute the authorised immutable R2 publication and full remote verification for the exact WP4F Discovery and Development releases bound by B1-G2.

Controls:
- Source workflow run: `30187276514`
- Publication order: payload first, manifest last
- Verification: full remote byte readback and SHA-256
- Selector activation: `NONE`
- C2 consumption: denied pending separate review
- Validation consumption: `LOCKED_UNCONSUMED`
