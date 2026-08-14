# ESLI-WP9 StructuralTerm Qualification Contract v0.1

Status: inactive deterministic conformance only. Authority effect: NONE.

This contract implements the ratified OPT-B StructuralTerm qualification boundary without admitting active vocabulary.

A `StructuralTermCandidate` owns a versioned machine symbol, term class, formal observable definition, observation unit, temporal semantics, inclusion/exclusion/boundary predicates, missingness/ambiguity policy, observable implications, falsifiers, prohibited interpretations, exact empirical scope and provenance. ResearchCandidateGeneration identity remains separate and is linked only through `LanguageCandidateBinding`.

Qualification rules are class-specific and MUST be frozen before evidence is inspected. `TermQualificationRecord` is reconstructible from exact rule-pack identity, stage statuses and named evidence dimensions. Mechanical replay is not empirical validity; EMPIRICALLY_OBSERVED requires frozen real-source population evidence; SEMANTICALLY_QUALIFIED requires an external governed adjudication decision reference.

WP9 exposes semantic-admission *proposals* only. `ADMITTED_ACTIVE` is rejected at the API boundary. Shadow admission can be proposed with expiry/provenance but cannot mutate an active registry. Challenge, quarantine, supersession, retirement and narrowing are proposal/review actions only. Historical term generations are immutable.

Cross-market/instrument/scale transport is represented only as `TRANSPORT_EVALUATION_CANDIDATE` with zero target-scope semantic authority and a new-evidence requirement.

Forbidden identity inputs include outcome, expected/future return, MFE/MAE, probability, forecast, risk, exposure, execution, trading, mechanism, cause and intent.
