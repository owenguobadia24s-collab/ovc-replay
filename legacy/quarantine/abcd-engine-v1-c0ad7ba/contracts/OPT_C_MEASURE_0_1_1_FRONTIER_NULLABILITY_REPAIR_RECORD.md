# OPT-C-MEASURE-0.1.1 Frontier Nullability Repair Record

**Decision:** `APPROVED DETERMINISTIC REPRESENTATION REPAIR`  
**Detected by:** `OPT-C-SEMANTIC-REVIEW-0.1`

The v0.1 semantic audit found 31 directional event–horizon rows—24 on the 15M
event clock and 7 on the 2H event clock—that named a primary frontier type while
the corresponding accepted frontier test was absent.

The repair makes the primary-frontier fields null in those cases. It changes no
source bar, path eligibility, anchor, price, return, excursion, continuation,
endpoint B-state, transition lineage or overlap value. All outcome record IDs
and release hashes are regenerated under `OPT-C-MEASURE-0.1.1`; v0.1 remains
preserved as superseded evidence.
