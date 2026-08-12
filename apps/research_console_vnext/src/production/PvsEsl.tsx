import type { ReactNode } from "react";
import "./pvsComponents.css";

type EslState = "PASS"|"OPEN"|"FAIL"|"DEFERRED"|"NA"|"UNAVAILABLE"|"LOCKED"|"BLOCKED"|"DENIED"|"PENDING"|"READY"|"KNOWN"|"UNRESOLVED"|"OPTIONAL"|"NOT_REQUIRED"|"NOT_EXECUTABLE"|"EXPECTED_ABSENCE"|"QUARANTINED"|"WARNING"|"REVIEW"|"NOT_RUN"|"FROZEN"|"COMPLETE"|"CURRENT"|"DEGRADED";

function EslCard({node,title,kicker,children,state}:{node:string;title:string;kicker:string;children:ReactNode;state?:string}) {
  return <article className="pvs-esl-card" data-figma-node={node} data-state={state}><small>{kicker}</small><h4>{title}</h4>{children}</article>;
}
function EslRow({node,label,detail,state}:{node:string;label:string;detail:string;state:EslState}) {
  return <div className="pvs-esl-row" data-figma-node={node}><strong>{label}</strong><code>{detail}</code><b data-state={state}>{state}</b></div>;
}

export type EpistemicPlane = "Structure"|"Organisation"|"Constraint"|"Mechanism";
export function EpistemicPlaneTab({plane,state="Default"}:{plane:EpistemicPlane;state?:"Default"|"Selected"|"Locked"}) {
  const detail:Record<EpistemicPlane,string>={Structure:"DIRECT OBSERVATION",Organisation:"POPULATION EVIDENCE",Constraint:"CONDITIONAL EVIDENCE",Mechanism:"RESEARCH THEORY ONLY"};
  return <button type="button" className="pvs-epistemic-tab" data-figma-node="202:40" data-plane={plane} data-state={state} data-navigation-only="true"><strong>{plane.toUpperCase()}</strong><small>{detail[plane]}</small></button>;
}

export function EvidenceStateBadge({state}:{state:"KNOWN"|"NOT_EVALUABLE"|"NULL"|"STALE"|"CENSORED"|"LOCKED"|"BLOCKED"}) {
  return <span className={`pvs-status pvs-status-${state==="KNOWN"?"pass":state==="BLOCKED"?"error":"warn"}`} data-figma-node="203:44"><i/><strong>{state}</strong></span>;
}

export function TopologyCard({identity,status="KNOWN",selected=false}:{identity:string;status?:EslState;selected?:boolean}) {
  return <EslCard node="204:26" kicker="STRUCTURAL ORGANISATION" title={identity} state={selected?"SELECTED":"DEFAULT"}><p>Topology identity is source text. Family is not privileged. Scientific status: <b data-state={status}>{status}</b>.</p></EslCard>;
}
export function EvidenceFrontierRow({field,source,state}:{field:string;source:string;state:"KNOWN"|"UNRESOLVED"|"OPTIONAL"|"NOT_REQUIRED"|"UNAVAILABLE"}) {return <EslRow node="205:32" label={field} detail={source} state={state}/>;}
export function QualificationRow({dimension,state}:{dimension:string;state:"FROZEN"|"PASS"|"OPEN"|"NOT_RUN"|"REVIEW"|"DENIED"}) {return <EslRow node="206:26" label={dimension} detail="whole-dossier qualification" state={state}/>;}

export function WorkflowStep({name,object,state}:{name:string;object:string;state:"PENDING"|"CURRENT"|"COMPLETE"|"DEGRADED"|"LOCKED"}) {return <EslRow node="224:32" label={name} detail={object} state={state}/>;}
export function EvidenceActionRow({action,target,locked=false}:{action:"OPEN"|"INSPECT"|"COMPARE"|"EXPAND"|"RETURN";target:string;locked?:boolean}) {return <EslRow node="225:32" label={action} detail={`${target} · authority_effect=NONE`} state={locked?"LOCKED":"READY"}/>;}
export function CompareScopeReceipt({population,cutoff,comparator,denominator,state="READY"}:{population:string;cutoff:string;comparator:string;denominator:string;state?:"READY"|"DEGRADED"|"BLOCKED"}) {return <EslCard node="226:47" kicker="COMPARISON SCOPE" title={state} state={state}><p>Population {population} · cutoff {cutoff} · comparator {comparator} · denominator {denominator}. Scope validity is not scientific promotion.</p></EslCard>;}
export function GovernedActionBoundary({action,reason}:{action:string;reason:string}) {return <EslCard node="227:32" kicker="OPERATOR-RESERVED BOUNDARY" title={action} state="LOCKED"><p>{reason}. Inspectable evidence remains available; mutation is not presented.</p></EslCard>;}

export type ExecutionProfile="BASE_STRUCTURAL"|"ORGANISATION_ENRICHED"|"CONSTRAINT_ENRICHED"|"FULL_RESEARCH";
export function ExecutionProfileCard({profile,dependencies}:{profile:ExecutionProfile;dependencies:string}) {return <EslCard node="239:22" kicker="EXECUTION PROFILE · NOT A RANKING" title={profile}><p>{dependencies}. Profile order has no scientific meaning.</p></EslCard>;}
export function ProfileAvailabilityState({profile,state}:{profile:ExecutionProfile;state:"READY"|"NOT_EXECUTABLE"|"UNAVAILABLE"}) {return <EslRow node="239:35" label={profile} detail="dependency/runtime availability" state={state}/>;}
export function MarginalEvidenceLedgerRow({profile,added,nullResidual,ambiguity,unavailable}:{profile:ExecutionProfile;added:number;nullResidual:number;ambiguity:number;unavailable:number}) {return <EslRow node="239:56" label={profile} detail={`added=${added}; null/residual=${nullResidual}; ambiguity=${ambiguity}; unavailable=${unavailable}; no aggregate score`} state="READY"/>;}
export function CapacityDeltaRow({profile,cold,warm,storage,fanout}:{profile:ExecutionProfile;cold:string;warm:string;storage:string;fanout:string}) {return <EslRow node="239:77" label={profile} detail={`cold=${cold}; warm=${warm}; storage=${storage}; fanout=${fanout}`} state="READY"/>;}

export function ResearchModeLane({mode,generation}:{mode:"PATH_1"|"PATH_2";generation:string}) {const display=mode==="PATH_1"?"Path 1":"Path 2";return <EslCard node="244:10" kicker="DUAL-MODE RESEARCH" title={`${display} · ${mode}`}><p>{display} provenance remains distinct until immutable ResearchCandidateGeneration {generation}.</p></EslCard>;}
export function LanguageCandidateBindingCard({generation,candidate}:{generation:string;candidate:string}) {return <EslCard node="244:31" kicker="IDENTITY-PRESERVING BINDING" title={candidate}><p>ResearchCandidateGeneration <code>{generation}</code> binds to StructuralTermCandidate without identity merge.</p></EslCard>;}
export function QualificationDimensionRow({dimension,state}:{dimension:string;state:"PASS"|"OPEN"|"FAIL"|"DEFERRED"|"NA"|"UNAVAILABLE"}) {return <EslRow node="244:62" label={dimension} detail="independent qualification dimension; no aggregate score" state={state}/>;}
export function SemanticAuthorityStage({stage,state}:{stage:"RESEARCH_FREEZE"|"TERM_DEFINITION_FREEZE"|"ACTIVE_SEMANTIC_ADMISSION";state:"READY"|"PENDING"|"LOCKED"}) {return <EslRow node="244:75" label={stage} detail="distinct authority event" state={state}/>;}
export function C3BridgeMaturityState({state}:{state:"INTERFACE_ONLY"|"FIXTURE"|"SHADOW_EVALUATION"|"PRODUCTION_GRAMMAR"}) {const locked=state==="SHADOW_EVALUATION"||state==="PRODUCTION_GRAMMAR";return <EslRow node="244:88" label="C3 BRIDGE MATURITY" detail={`technical maturity=${state}; technical maturity ≠ semantic authority`} state={locked?"LOCKED":"READY"}/>;}

export function TheoryStatusCard({theory,version,state}:{theory:string;version:string;state:"OPEN"|"SUPPORTED"|"CONTRADICTED"|"DEFERRED"}) {const mapped:EslState=state==="SUPPORTED"?"PASS":state==="CONTRADICTED"?"FAIL":state==="DEFERRED"?"DEFERRED":"OPEN";return <EslCard node="249:60" kicker={`THEORY ${version} · EVIDENCE STATE`} title={theory} state={mapped}><p>Versioned theory status is evidence state, not truth by colour.</p></EslCard>;}
export function ExperimentLifecycleCard({experiment,state}:{experiment:string;state:"DRAFT"|"PREREGISTERED"|"EXECUTION"|"QA"|"DISPOSITION"}) {return <EslCard node="249:89" kicker="EXPERIMENT LIFECYCLE" title={experiment} state={state}><p>{state} · lifecycle state does not grant scientific authority.</p></EslCard>;}
export function EvidenceBalanceRow({claim,support,contradiction}:{claim:string;support:number;contradiction:number}) {return <EslRow node="249:115" label={claim} detail={`support + contradiction co-visible; support=${support}; contradiction=${contradiction}`} state="READY"/>;}
export function HealthDomainSignal({domain,freshness,source,affected,state}:{domain:string;freshness:string;source:string;affected:string;state:"PASS"|"WARNING"|"BLOCKED"}) {return <EslRow node="249:140" label={domain} detail={`freshness=${freshness}; source=${source}; affected=${affected}; no composite score`} state={state}/>;}
export function AgentCapabilityState({level,state}:{level:"A0 Observer"|"A1 Analyst"|"A2 Planner"|"A3 Runner"|"A4 Patchwright"|"A5 Release Steward";state:"READY"|"LOCKED"|"DENIED"}) {return <EslRow node="249:165" label={level} detail="independently evaluated and revocable; never self-approving" state={state}/>;}
export function EHReadinessState({state}:{state:"NOT_READY"|"EVIDENCE_READY"|"DECISION_READY"|"LOCKED"}) {return <EslCard node="249:190" kicker="E-H READINESS · NOT EXPOSURE AUTHORITY" title={state} state={state}><p>Evidence readiness and decision readiness do not grant exposure authority.</p></EslCard>;}

export function AssuranceAssertionCard({plane,result}:{plane:"ScientificSemantic"|"AuthoritySafety"|"Accessibility"|"PerformanceCapacity"|"LocalOperation";result:"PASS"|"BLOCKED"}) {return <EslCard node="259:52" kicker="INDEPENDENT ASSURANCE PLANE" title={plane} state={result}><p>{result}. Assurance PASS grants no scientific or interface authority.</p></EslCard>;}
export function AdversarialCaseRow({caseId,outcome}:{caseId:string;outcome:"PASS"|"BLOCKED"|"DENIED"|"QUARANTINED"|"EXPECTED_ABSENCE"}) {return <EslRow node="259:78" label={caseId} detail="adversarial assurance result" state={outcome}/>;}
export function ViewportAssuranceCard({viewport,result="PASS"}:{viewport:"1920x1080"|"1440x810"|"1280x720";result?:"PASS"|"BLOCKED"}) {return <EslCard node="259:94" kicker="RESPONSIVE ASSURANCE" title={viewport} state={result}><p>{result} · critical identity/authority/FVT/missingness/denominator semantics remain visible.</p></EslCard>;}
export function CapacityBudgetRow({metric,value,state="PASS"}:{metric:"Payload"|"Cache"|"Graph"|"Population"|"CanvasHeight";value:string;state?:"PASS"|"WARNING"|"BLOCKED"}) {return <EslRow node="259:120" label={metric} detail={`${value}; CAPACITY_EXCEEDED typed; no silent sampling`} state={state}/>;}
export function RollbackReceiptCard({state,receipt}:{state:"READY"|"REHEARSED"|"FAILED"|"BLOCKED";receipt:string}) {const mapped:EslState=state==="REHEARSED"?"PASS":state==="FAILED"?"FAIL":state;return <EslCard node="259:141" kicker="ROLLBACK RECEIPT" title={state} state={mapped}><p>{receipt}. Restore accepted local build without source/scientific authority change.</p></EslCard>;}
export function AcceptanceCriterionState({criterion,state}:{criterion:string;state:"PASS"|"WARNING"|"BLOCKED"|"PENDING"|"EXCEPTION_ACCEPTED"}) {const mapped:EslState=state==="EXCEPTION_ACCEPTED"?"REVIEW":state;return <EslRow node="259:162" label={criterion} detail="acceptance evidence; operator acceptance distinct from assurance PASS" state={mapped}/>;}
