import { useLocation } from "react-router-dom";
import "./researchNative.css";

type BadgeProps={label:string;value:string};
export function ObjectBadge({label,value}:BadgeProps){return <span className="rnBadge"><b>{label}</b> {value}</span>}
export const AuthorityBadge=({value}:{value:string})=><ObjectBadge label="AUTHORITY" value={value}/>;
export const AvailabilityBadge=({value}:{value:string})=><ObjectBadge label="AVAILABILITY" value={value}/>;
export const QAStatus=({value}:{value:string})=><ObjectBadge label="QA" value={value}/>;
export const ReasonCode=({value}:{value:string})=><ObjectBadge label="REASON" value={value}/>;
export const ChronologyChip=({value}:{value:string})=><ObjectBadge label="FVT" value={value}/>;
export const TypedObjectLink=({type,id}:{type:string;id:string})=><span className="rnObject">{type} · {id}</span>;

const domainFor=(path:string)=>path.startsWith('/research')?'RESEARCH':path.startsWith('/evidence')?'EVIDENCE':path.startsWith('/control')?'CONTROL':'INVESTIGATE';
export function EvidencePassport(){return <div className="rnStack"><h3>Evidence Passport</h3><TypedObjectLink type="SYNTHETIC_FIXTURE" id="RN-DEMO-001"/><AuthorityBadge value="NONE"/><AvailabilityBadge value="AVAILABLE"/><ChronologyChip value="2026-06-22T08:00:00Z"/><QAStatus value="PASS"/><ReasonCode value="NON_EVIDENTIARY"/></div>}
export function DegradedState({kind,why,impact}:{kind:string;why:string;impact:string}){return <section className="rnDegraded" role="status"><strong>{kind}</strong><span>Why: {why}</span><span>Impact: {impact}</span><span>Unaffected: identity · authority · evidence trace</span></section>}
export function WorkbenchFrame(){const d=domainFor(useLocation().pathname);return <div className="rnFrame"><nav className="rnNav" aria-label="Research domains"><strong>{d}</strong><span>Investigate</span><span>Research</span><span>Evidence</span><span>Control</span></nav><main className="rnCanvas"><header><p className="rnKicker">RESEARCH-NATIVE · FIXTURE ONLY</p><h1>{d} Workbench</h1><p>Source-bound research projection. Price is optional context, not the product identity.</p></header><DegradedState kind="NOT_MATERIALIZED" why="Owning source is not materialized" impact="Dependent view is withheld"/></main><aside className="rnInspector"><h2>Inspector</h2><p>Selected object semantics remain source-owned.</p></aside><aside className="rnDock"><EvidencePassport/></aside></div>}
