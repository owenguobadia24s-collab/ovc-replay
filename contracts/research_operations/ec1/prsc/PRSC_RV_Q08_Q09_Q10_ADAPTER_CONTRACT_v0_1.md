# PRSC RV/Q08/Q09/Q10 Adapter Contract v0.1

PRSCI-WP11 build-ahead is adapter/schema only. It extends existing EC1 review surfaces by reference and MUST NOT create a competing review store, mutate candidate semantics, activate capabilities, or execute CandidateFreeze.

Adapters bind PRSC execution/challenge/review/disposition references into EvidenceCycleReviewPacket and P1CandidateReviewCard-compatible projections. Reviewer disagreement remains explicit and cannot be reduced by majority vote.

METHOD_LIMITATION, INFORMATION_LIMITATION, DATA_GAP and AUTHORITY_LIMITATION may be emitted only as recommendation/routing references for RCCR/Q09. They have authority_effect=NONE and cannot self-activate an owner capability.

A CandidateFreezeRecommendation may point only to existing EC1-GSCI; this build-ahead layer cannot execute or approve that gate. Research Console projection remains deferred until backend correctness and consumer-owner source admission.