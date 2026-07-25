# Reference-Level Registry Validation

**Validation ID:** `B-REF-0.1-VALIDATION-2026-07-19`  
**Status:** `PASS`

## Verified

- All OPT-A seal artifact hashes passed.
- All registry artifact hashes passed.
- Rebuilding from the sealed canonical bars reproduced every stored level exactly.
- All 12,977 reference-level IDs are unique across 15M and 2H.
- No swing or range construction window crosses a source gap.
- Stored level prices, construction bars and first-valid timestamps are future-stable.
- Candidate eligibility begins no earlier than the candidate open after the level became knowable.

## Test suite

The dependency-free implementation passes 32 unit and property-focused tests, including eight registry-specific tests for swing confirmation, tie rejection, gap isolation, range-boundary emission, deterministic IDs, future stability, eligibility timing and reordered-input rejection.

## Boundary

This validation proves deterministic construction and reproducibility. It does not prove that any level type predicts an outcome or should be exposed as an active trading signal.
