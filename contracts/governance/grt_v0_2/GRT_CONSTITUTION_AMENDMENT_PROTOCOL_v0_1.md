# GRT Constitution Amendment Protocol v0.1

**Authority:** `OPERATOR_REQUIRED`

A change to rule semantics, root legality, owner cardinality, exemption semantics, lifecycle boundaries, debt effect, or current/historical meaning is a constitutional authority change.

Required sequence:

1. versioned `ConstitutionAmendmentProposal`;
2. exact source and candidate Constitution hashes;
3. rule-by-rule and finding/debt impact analysis;
4. dual or shadow evaluation against qualified reference semantics;
5. explicit finding and DebtFloor migration plan;
6. operator decision;
7. new immutable Constitution generation;
8. separately governed activation.

Implementation optimization that preserves the exact canonical Constitution hash is not an amendment. A runtime defect cannot be used to silently make enforcement advisory.
