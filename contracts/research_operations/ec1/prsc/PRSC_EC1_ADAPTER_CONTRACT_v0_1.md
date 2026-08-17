# PRSC EC1 Adapter Contract v0.1

PRSC extends existing EC1 review records additively. It does not duplicate or replace owner authority for P1CandidateReviewCard, QuestionDecisionRecord or EvidenceCycleReviewPacket.

A conformant adapter:
1. preserves every owner-defined source field unchanged;
2. may add only typed `prsc_refs` / PRSC read-model projections;
3. treats absence of PRSC references on historical EC1 records as lawful;
4. never changes candidate definition, membership, mechanical proposal eligibility, Q02-Q04 recurrence facts, or CandidateFreeze state;
5. routes METHOD_LIMITATION / INFORMATION_LIMITATION / DATA_GAP / AUTHORITY_LIMITATION as evidence only.
