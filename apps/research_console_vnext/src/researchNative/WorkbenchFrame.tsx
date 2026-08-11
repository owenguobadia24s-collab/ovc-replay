import { useLocation } from "react-router-dom";
import { SemanticRiskGallery } from './SemanticRiskPrototypes';
import "./researchNative.css";
import "./researchNativeNarrow.css";

type BadgeProps = { label: string; value: string };
export function ObjectBadge({ label, value }: BadgeProps) { return <span className="rnBadge"><b>{label}</b><span>{value}</span></span>; }
export const AuthorityBadge = ({ value }: { value: string }) => <ObjectBadge label="AUTHORITY" value={value}/>;
export const AvailabilityBadge = ({ value }: { value: string }) => <ObjectBadge label="AVAILABILITY" value={value}/>;
export const QAStatus = ({ value }: { value: string }) => <ObjectBadge label="QA" value={value}/>;
export const ReasonCode = ({ value }: { value: string }) => <ObjectBadge label="REASON" value={value}/>;
export const ChronologyChip = ({ value }: { value: string }) => <ObjectBadge label="FVT" value={value}/>;
export const TypedObjectLink = ({ type, id }: { type: string; id: string }) => <span className="rnObject"><small>{type}</small><strong>{id}</strong></span>;

const domainFor = (path: string) => path.startsWith('/research') ? 'RESEARCH' : path.startsWith('/evidence') ? 'EVIDENCE' : path.startsWith('/control') ? 'CONTROL' : 'INVESTIGATE';
const domainQuestion: Record<string,string> = {
  INVESTIGATE: 'What happened, what structure exists, and what exact evidence supports it?',
  RESEARCH: 'What distinction is under study, how stable is it, and what contradicts it?',
  EVIDENCE: 'Why is this object lawful and what exact lineage, QA and source evidence supports it?',
  CONTROL: 'What can the OVC system lawfully do, what is blocked, and why?',
};

export function EvidencePassport() { return <div className="rnPassport"><div><span className="rnPanelCode">E1</span><div><small>EVIDENCE PASSPORT</small><strong>RN-DEMO-001</strong></div></div><div className="rnPassportBadges"><AuthorityBadge value="NONE"/><AvailabilityBadge value="AVAILABLE"/><ChronologyChip value="08:15Z"/><QAStatus value="PASS"/></div></div>; }
export function DegradedState({ kind, why, impact }: { kind: string; why: string; impact: string }) { return <section className="rnDegraded" role="status"><div><strong>{kind}</strong><span>DEGRADED SOURCE</span></div><p>You are seeing <b>{kind}</b> because {why}; this affects <b>{impact}</b>; it does not affect identity, authority or the evidence trace.</p><ReasonCode value="UPSTREAM_READ_MODEL_GAP"/></section>; }

export function WorkbenchFrame() {
  const domain = domainFor(useLocation().pathname);
  return <section className="rnFrame" data-density="analytical" aria-label={`${domain} fixture workbench`}>
    <div className="rnWorkbenchGrid">
      <aside className="rnNav rnContextNavigator" aria-label="Research object navigator">
        <div className="rnPanelHeader"><span className="rnPanelCode">A</span><strong>Context Navigator</strong><button type="button" data-navigation-only="true" aria-label="Navigator menu">•••</button></div>
        <div className="rnFilterBox">⌕ <input aria-label="Filter research objects" placeholder="Filter research objects…" readOnly/><button type="button" data-navigation-only="true">▽</button></div>
        <div className="rnSectionLabel">RESEARCH DOMAIN</div>
        <div className="rnDomainStack">{['Investigate','Research','Evidence','Control'].map((item) => <div key={item} data-active={item.toUpperCase() === domain}><i/><span>{item}</span><small>{item.toUpperCase() === domain ? 'ACTIVE' : 'AVAILABLE'}</small></div>)}</div>
        <div className="rnSectionLabel">SELECTED FIXTURE</div>
        <div className="rnSelectedObject"><small>SYNTHETIC_FIXTURE</small><strong>RN-DEMO-001</strong><span>NON_EVIDENTIARY</span></div>
        <div className="rnSectionLabel">STRUCTURAL DIMENSIONS</div>
        <div className="rnAxisList">{[['LOCATION','OBSERVED'],['MOTION','OBSERVED'],['ORGANISATION','NOT_EVALUABLE'],['INTERACTION','OBSERVED']].map(([axis,state]) => <div key={axis}><i data-state={state}/><span>{axis}</span><b>{state}</b></div>)}</div>
        <div className="rnNavigatorFooter"><span>PIPELINE</span><strong>OPT-A → C1 → C2 → C2E → C2P → C2.5 → C3</strong><small>Orientation only · scientific ownership unchanged</small></div>
      </aside>

      <main className="rnCanvas">
        <div className="rnCanvasHeader"><div><p className="rnKicker">RESEARCH-NATIVE · FIXTURE ONLY · ANALYTICAL</p><h1>{domain} Workbench</h1><p>{domainQuestion[domain]}</p></div><div className="rnCanvasIdentity"><TypedObjectLink type="SELECTED" id="RN-DEMO-001"/><span className="rnSourceDot">SOURCE BOUND</span></div></div>
        <div className="rnCanvasToolbar"><div className="rnViewTabs"><button className="isActive" type="button" data-navigation-only="true">STRUCTURAL EVIDENCE</button><button type="button" data-navigation-only="true">PROOF</button><button type="button" data-navigation-only="true">SEMANTICS</button><button type="button" data-navigation-only="true">LINEAGE</button></div><div className="rnToolbarActions"><button type="button" data-navigation-only="true">Density: Analytical</button><button type="button" data-navigation-only="true">⌁ Evidence</button><button type="button" data-navigation-only="true">⋮</button></div></div>
        <DegradedState kind="NOT_MATERIALIZED" why="the owning C2E source is not materialized" impact="dependent episode views only"/>
        <div className="rnSemanticCanvas"><SemanticRiskGallery/></div>
      </main>

      <aside className="rnInspector" aria-label="Evidence Inspector">
        <div className="rnPanelHeader"><span className="rnPanelCode">C</span><strong>Evidence Inspector</strong><span className="rnInspectorTools">☆ ⧉</span></div>
        <section className="rnInspectorIdentity"><small>OBJECT IDENTITY</small><strong>RN-DEMO-001</strong><span>SYNTHETIC</span></section>
        <section><h3>Authority state</h3><div className="rnAuthorityTriad"><div><small>AVAILABLE</small><strong>YES</strong></div><div><small>AUTHORISED</small><strong>NO</strong></div><div><small>ACTIVE</small><strong>NO</strong></div></div><p>Fixture-only presentation · authority_effect=NONE.</p></section>
        <section><h3>Chronology</h3><dl className="rnInspectorList"><div><dt>Effective time</dt><dd>08:00:00Z</dd></div><div><dt>First-valid time</dt><dd>08:15:00Z</dd></div><div><dt>Evaluation cutoff</dt><dd>08:15:00Z</dd></div><div><dt>Clock</dt><dd>15M / 2H-B</dd></div></dl></section>
        <section><h3>Availability & missingness</h3><div className="rnAvailabilityRows"><div><i data-state="OBSERVED"/><span>C2 structural evidence</span><b>AVAILABLE</b></div><div><i data-state="NOT_EVALUABLE"/><span>C2E episode owner</span><b>NOT_MATERIALIZED</b></div><div><i data-state="OBSERVED"/><span>C3 AST fixture</span><b>AVAILABLE</b></div></div></section>
        <div className="rnInspectorAccordion">{['STRUCTURAL PAYLOAD','DEPENDENCIES','QA ASSERTIONS','LINEAGE & SUPERSESSION','CANONICAL RAW PAYLOAD'].map((label) => <button key={label} type="button" data-navigation-only="true"><span>{label}</span><b>{label === 'QA ASSERTIONS' ? 'PASS' : '›'}</b></button>)}</div>
      </aside>
    </div>

    <aside className="rnDock" aria-label="Evidence Dock">
      <article className="rnDockCard"><EvidencePassport/></article>
      <article className="rnDockCard"><div className="rnDockHeader"><span className="rnPanelCode">E2</span><strong>Missingness</strong></div><div className="rnDockMetric"><strong>1 / 4</strong><span>structural dimensions not evaluable</span><small>Exact denominator preserved</small></div></article>
      <article className="rnDockCard"><div className="rnDockHeader"><span className="rnPanelCode">E3</span><strong>QA & Provenance</strong></div><div className="rnDockMetric"><strong>PASS</strong><span>fixture contract · source identity · chronology</span><small>Renderer adds no scientific values</small></div></article>
      <article className="rnDockCard rnDockWide"><div className="rnDockHeader"><span className="rnPanelCode">E4</span><strong>Evidence & Change Conditions</strong></div><div className="rnConditionGrid"><div><small>SUPPORT</small><strong>C2 LOCATION observed</strong></div><div><small>CONTRADICTION</small><strong>ORGANISATION not evaluable</strong></div><div><small>NEXT WATCH</small><strong>C2E source materialization</strong></div></div></article>
    </aside>
  </section>;
}
