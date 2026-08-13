# GRT Bootstrap Validation Contract v0.1

**Profile:** `ovc-grt-bootstrap-subset-v1`  
**Validator release:** `ovc-grt-bootstrap-validator/1.0.0`  
**Authority effect:** `NONE_BOOTSTRAP_ONLY`

WP1 uses a finite validator because the full GRT runtime does not yet exist. The validator supports an explicit subset of JSON Schema Draft 2020-12 and rejects unknown dialects, unknown keywords, malformed bounds, cyclic manifest dependencies, self-referential in-memory schemas, duplicate registry identities, malformed instances, and unclassified registry drift.

The bootstrap validator must not depend on future GRT registries or runtime services. It validates only this packet's schemas, registry entries, manifest DAG and canonical reconstruction. WP3 supersedes it as the complete reference runtime; bootstrap PASS is not enforcement qualification.
