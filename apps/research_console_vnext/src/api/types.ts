import type { components } from "./generated/schema";

export type FixtureBanner = components["schemas"]["FixtureBanner"];
export type SourceIdentity = components["schemas"]["SourceIdentity"];
export type CapabilityDependencyStatus = components["schemas"]["CapabilityDependencyStatus"];
export type Investigation = components["schemas"]["Investigation"];

export type CapabilitySummary = {
  capability_id: string;
  available: boolean;
  authorised: boolean;
  active: boolean;
  authority_effect: "NONE";
};

export type ReadEnvelope<T> = {
  fixture_banner: FixtureBanner;
  schema_id: string;
  resource: string;
  source_identity: SourceIdentity;
  capability: CapabilitySummary;
  payload: T;
};

export type MarketBar = { t: string; o: number; h: number; l: number; c: number };
export type MarketWindow = { items: MarketBar[]; total: number; truncated: boolean };
export type C2StateView = {
  availability: string;
  axes: Record<string, string>;
  computability: Record<string, string>;
  first_valid_time?: string;
};
export type C2EView = {
  availability: string;
  reason_code?: string;
  episodes: unknown[];
  events: unknown[];
};
export type OccurrenceContextView = {
  instrument?: string;
  clock?: string;
  side?: string;
  session?: string;
  occurrence_id: string;
  context_id?: string;
  source?: string;
  availability?: string;
  reason_code?: string;
};
export type EvidenceItem = { evidence_id: string; kind: string; record_ref: string };
export type EvidencePage = { items: EvidenceItem[]; next_cursor: number | null; total: number };
export type FamilyEvidenceView = {
  family_id: string | null;
  assignment_status: string;
  reason_code?: string;
  authority_effect?: "NONE";
};

export type WP5ASourcePreflight = {
  status: "PASS_NO_FIRST_NEW_REAL_RESEARCH_SOURCE";
  gate_branch: "RCN-RN-WP5A-CLOSEOUT";
  operator_escalation_gate: "RCN-RN-G5-FIRST-NEW-SOURCE";
  first_new_real_research_source: false;
  source_binding_registry: string;
  source_ids: string[];
};

export type WP5AMethod = {
  method_id: string;
  basis: string;
  source_id: string;
  source_fixture_id: string;
  status: string;
  disposition: string;
  winner: null;
  selection_authority: "NONE";
};

export type WP5AComparison = {
  comparison_id: string;
  source_id: string;
  source_fixture_id: string;
  status: "NOT_COMPARABLE" | "AMBIGUOUS" | "TIE_RETAINED";
  distance_engine_called: boolean;
  winner: null;
};

export type WP5AFamilyOutcome = {
  outcome: "RESIDUAL" | "AMBIGUOUS" | "NO_STABLE_FAMILY";
  status: "LAWFUL_EQUAL_STATUS";
  count: number;
  source_id: string;
  source_fixture_id: string;
  authority_effect: "NONE";
};

export type WP5ARepresentationSnapshot = {
  schema: "ovc-rcn-rn-wp5a-representation-snapshot/v1";
  packet_id: "RCN-RN-WP5A";
  mode: "FIXTURE_ONLY";
  data_classification: "SYNTHETIC_FIXTURE";
  evidence_status: "NON_EVIDENTIARY";
  authority_effect: "NONE";
  source_preflight: WP5ASourcePreflight;
  population: {
    population_id: string;
    evaluable_count: number;
    missing_count: number;
    denominator: number;
    truncated: boolean;
  };
  source_fixture_refs: Array<{ source_id: string; fixture_id: string; expected: string }>;
  methods: WP5AMethod[];
  comparability: WP5AComparison[];
  family_outcomes: WP5AFamilyOutcome[];
  outcome_denominator: {
    residual_count: number;
    ambiguous_count: number;
    no_stable_family_count: number;
    denominator: number;
  };
  sensitivity: Array<{
    source_id: string;
    source_fixture_id: string;
    status: string;
    expected: string;
    winner: null;
  }>;
  mcarb: Array<{
    source_id: string;
    source_fixture_id: string;
    status: string;
    expected: string;
  }>;
  presentation_guardrails: {
    method_first: true;
    family_first: false;
    default_winner: null;
    scientific_strength_score: null;
    frontend_scientific_calculation: "PROHIBITED";
    selector_authority: "NONE";
    writes: "NONE";
    validation_consumption: "LOCKED_UNCONSUMED";
    equal_status_outcomes: Array<"RESIDUAL" | "AMBIGUOUS" | "NO_STABLE_FAMILY">;
    no_forced_assignment: true;
    correspondence_is_independence: false;
  };
};

export type WP5B1DMRPSnapshot = {
  schema: "ovc-rcn-rn-wp5b1-dmrp-snapshot/v1";
  packet_id: "RCN-RN-WP5B1";
  mode: "FIXTURE_ONLY";
  data_classification: "SYNTHETIC_FIXTURE";
  evidence_status: "NON_EVIDENTIARY";
  authority_effect: "NONE";
  source_preflight: {
    status: "PASS_NO_FIRST_NEW_REAL_RESEARCH_SOURCE";
    gate_branch: "RCN-RN-WP5B1-CLOSEOUT";
    operator_escalation_gate: "RCN-RN-G5-FIRST-NEW-SOURCE[DMRP]";
    first_new_real_research_source: false;
    source_binding_registry: string;
    source_ids: string[];
  };
  path1: {
    research_mode: "PATH_1_EMPIRICAL";
    research_role: string;
    study_id: string;
    cycle_id: string;
    question_id: string;
    validation_access_state: "LOCKED_UNCONSUMED";
    source_id: string;
  };
  path2: {
    training_id: string;
    guided_formalisation_id: string;
    ready_intake_id: string;
    divergent_intake_id: string;
    divergent_disposition: string;
    real_source_authority: "NONE";
    source_id: string;
  };
  candidate_generation: {
    series_id: string;
    origin_mode: "PATH_1_EMPIRICAL";
    generation: number;
    population_id: string;
    required_dependencies: string[];
    membership: Record<string, number>;
    source_id: string;
  };
  cross_mode: Array<{
    relation_id: string;
    path1_candidate_series_id: string;
    path2_theory_id: string;
    correspondence: string;
    independence: string;
    identity_merge: false;
    winner: null;
    ranking: null;
  }>;
  negative_divergent_evidence: Array<{
    evidence_id: string;
    mode: string;
    status: string;
    count: number;
  }>;
  presentation_guardrails: {
    candidate_construction: "PROHIBITED";
    candidate_repair: "PROHIBITED";
    candidate_identity_merge: "PROHIBITED";
    candidate_promotion: "NONE";
    path_winner: null;
    ranking: "NONE";
    correspondence_is_independence: false;
    missing_exposure_implies_independence: false;
    frontend_scientific_calculation: "PROHIBITED";
    writes: "NONE";
    validation_consumption: "LOCKED_UNCONSUMED";
    first_new_real_research_source: false;
  };
};
