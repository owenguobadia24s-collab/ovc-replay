export type Domain = "Investigate" | "Research" | "Evidence" | "Control";

export type RouteConfig = {
  domain: Domain;
  kicker: string;
  title: string;
  subtitle: string;
  navigatorTitle: string;
  selectedObject: string;
  objectType: string;
  source: string;
  generation: string;
  population: string;
  instrument: string;
  clock: string;
  fvt: string;
  nav: readonly (readonly [string, string])[];
};

export const ROUTES: Record<string, RouteConfig> = {
  "/structure": {
    domain:"Investigate", kicker:"INVESTIGATE / STRUCTURE", title:"C2 structural state matrix + synchronized C2E episode rail",
    subtitle:"fixture projection · exact cutoff 16:55Z · source-bound · no reconstructed upper layer",
    navigatorTitle:"STRUCTURE / OCCURRENCE", selectedObject:"C2:OBS:8598:2417", objectType:"C2Observation",
    source:"RCN-P4-INV-STRUCT", generation:"vNext-PVS2", population:"8,598", instrument:"GBP/USD", clock:"15M / 2H", fvt:"2026-08-11 16:55Z",
    nav:[["Structure","214"],["Translation","8,598"],["Objects","142"],["Events","421"],["Semantics","C3"],["Chronology","FVT"]],
  },
  "/research": {
    domain:"Research", kicker:"RESEARCH / REPRESENTATIONS", title:"Representation, distance and family-stability comparison",
    subtitle:"method-first fixture · no default winner · residual / ambiguity / NO_STABLE_FAMILY are lawful",
    navigatorTitle:"REPRESENTATION / METHOD", selectedObject:"REP:R3-HYBRID-v2", objectType:"RepresentationComparison",
    source:"RCN-P4-RES-REP", generation:"SRFD-SHADOW", population:"1,240", instrument:"GBP/USD", clock:"15M / 2H", fvt:"2026-08-11 16:55Z",
    nav:[["Representations","12"],["Comparability","PAIR"],["Families","37"],["Sensitivity","6"],["Research Ops","3"],["Evaluation","A–D"]],
  },
  "/research/representations": {
    domain:"Research", kicker:"RESEARCH / WP5A SOURCE-BOUND REPRESENTATIONS", title:"SRI, FDI, SRFD and MCARB representation evidence",
    subtitle:"synthetic fixture · non-evidentiary · exact source blobs verified · no first-new real Research source",
    navigatorTitle:"WP5A / METHOD-FIRST", selectedObject:"RCN-RN-WP5A", objectType:"RepresentationReadSurface",
    source:"WP5A-FIXTURE-BINDINGS-v1", generation:"RCN-RN-v0.3", population:"7 fixture methods", instrument:"GBP/USD", clock:"15M / 2H", fvt:"FIXTURE / NO MARKET FVT",
    nav:[["Methods","7"],["Comparability","5"],["Outcomes","3"],["Sensitivity","3"],["MCARB","3"],["Authority","NONE"]],
  },
  "/evidence": {
    domain:"Evidence", kicker:"EVIDENCE / LINEAGE", title:"Bounded lineage, dependency and QA projection",
    subtitle:"selected object C2E:EP:00421 · source receipt pinned · no silent stale redirect",
    navigatorTitle:"TRUTH / LINEAGE", selectedObject:"C2E:EP:00421", objectType:"EpisodeSnapshot",
    source:"RCN-P4-EVD-LIN", generation:"LINEAGE-V1", population:"214", instrument:"GBP/USD", clock:"15M / 2H", fvt:"2026-08-11 16:55Z",
    nav:[["Lineage","214"],["Overview","1"],["QA","12"],["Artifacts","9"],["Runs","3"],["Raw payload","JSON"]],
  },
  "/control": {
    domain:"Control", kicker:"CONTROL / PROGRAMMES + AUTHORITY", title:"Programme state, gates, authority and dependency consequences",
    subtitle:"read-only fixture projection · repo state is court record · no approvals or run controls",
    navigatorTitle:"SYSTEM / GOVERNANCE", selectedObject:"PVS2-WP1", objectType:"ProgrammeState",
    source:"FIXTURE-PVS2-CONTROL", generation:"CONTROL-PVS2", population:"PROGRAMME FIXTURE", instrument:"OVC SYSTEM", clock:"REPO / UTC", fvt:"2026-08-12 17:57Z",
    nav:[["Programmes","FIXTURE"],["Authority","READ_ONLY"],["Gates","RESERVED"],["Dependencies","BOUND"],["Health","MULTI"],["Repository","COURT RECORD"],["Orchestration","READ"]],
  },
};

export const domainColor = (domain: Domain) => `var(--ovc-domain-${domain.toLowerCase()})`;
export const domainPath: Record<Domain,string> = { Investigate:"/structure", Research:"/research", Evidence:"/evidence", Control:"/control" };
export const DOMAINS: readonly Domain[] = ["Investigate","Research","Evidence","Control"];
