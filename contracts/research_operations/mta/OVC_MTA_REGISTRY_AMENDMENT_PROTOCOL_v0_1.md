# OVC MTA Registry Amendment Protocol v0.1

1. Detect a classification, metric, reason-code or routing error.
2. Freeze `REGISTRY_AMENDMENT_<n>.json` with prior/new registry IDs, exact diff, rationale, evidence, affected packets and reruns.
3. Create a new immutable registry version; never edit or delete the prior version.
4. Bind existing outputs to the version that produced them and mark affected outputs `STALE_PENDING_RERUN`.
5. Material amendments stop for operator `ACKNOWLEDGE`, `HOLD`, `BLOCK` or `QUARANTINE`. Non-material metadata corrections may wait for MTA-A3 or MTA-A6.
6. Recompute all affected metrics, clusters and readiness records.
7. Publish a supersession map from stale outputs to rerun outputs.

No audit output may silently inherit a changed registry meaning.
