import type { CSSProperties } from "react";
import { NavLink } from "react-router-dom";
import { DOMAINS, domainColor, domainPath, type Domain, type RouteConfig } from "./pvsContracts";

const railGlyphs: Record<Domain,string> = { Investigate:"⌁", Research:"◇", Evidence:"▣", Control:"⌘" };

export function GlobalDomainRail({ domain }: { domain: Domain }) {
  return <aside className="pc-rail" data-rcn-ref="production-domain-rail" data-figma-node="44:159" aria-label="Global domain rail">
    <div className="pc-logo">OVC</div>
    <nav>{DOMAINS.map(item=><NavLink key={item} to={domainPath[item]} className={item===domain?"pc-rail-link active":"pc-rail-link"} style={{"--domain":domainColor(item)} as CSSProperties} aria-label={item}><span aria-hidden="true">{railGlyphs[item]}</span></NavLink>)}</nav>
    <div className="pc-rail-utils" aria-label="Navigation utilities"><span aria-hidden="true">⚙</span><span aria-hidden="true">?</span></div>
  </aside>;
}

export function ApplicationHeader({ domain }: { domain: Domain }) {
  return <header className="pc-header" data-rcn-ref="production-header" data-figma-node="46:213">
    <div className="pc-brand"><strong>Research Console vNext</strong><small>Research operating environment</small></div>
    <nav className="pc-domain-tabs" aria-label="Research Console domains">{DOMAINS.map(item=><NavLink key={item} to={domainPath[item]} className={item===domain?"active":""} style={{"--domain":domainColor(item)} as CSSProperties}>{item.toUpperCase()}</NavLink>)}</nav>
    <div className="pc-investigation">IROF-GOLDEN2</div>
    <div className="pc-search" data-navigation-only="true">⌕ <span>Search object, ID, command…</span><kbd>⌘K</kbd></div>
    <div className="pc-readonly">READ ONLY</div>
    <div className="pc-operator"><strong>RESEARCH_OPERATOR</strong><small>local · fixture-safe</small><i/></div>
  </header>;
}

export function ContextAuthorityStrip({ cfg }: { cfg: RouteConfig }) {
  const cells = [
    ["INSTRUMENT",cfg.instrument],["CLOCK",cfg.clock],["MODE",cfg.domain==="Control"?"READ_ONLY":"SYNTHETIC_FIXTURE"],["POPULATION",cfg.population],
    ["SOURCE",cfg.source],["GENERATION",cfg.generation],["FVT",cfg.fvt],["AVAILABLE","YES"],["AUTHORISED","YES"],["ACTIVE","NO"],["AUTHORITY EFFECT","NONE"],["FRESHNESS","FIXTURE"],
  ];
  return <div className="pc-context" data-rcn-ref="production-context-strip" data-figma-node="47:292" aria-label="Source context and independent authority state">{cells.map(([label,value])=><div key={label} className={`pc-context-cell ${label.toLowerCase().replace(/ /g,"-")}`}><small>{label}</small><strong>{value}</strong></div>)}</div>;
}

export function WorkbenchNavigator({ cfg }: { cfg: RouteConfig }) {
  const fvt = cfg.fvt.includes(" ") ? cfg.fvt.split(" ").at(-1) : cfg.fvt;
  return <aside className="pc-navigator" data-rcn-ref="production-navigator" data-figma-node="49:338">
    <small className="pc-domain-label" style={{color:domainColor(cfg.domain)}}>{cfg.domain.toUpperCase()}</small>
    <h2>{cfg.navigatorTitle}</h2><div className="pc-rule"/>
    <nav>{cfg.nav.map(([label,meta],index)=><div key={label} className={index===0?"pc-nav-row active":"pc-nav-row"} style={index===0?{"--domain":domainColor(cfg.domain)} as CSSProperties:undefined} data-selection-state={index===0?"SELECTED":"AVAILABLE"}><span>{label}</span><code>{meta}</code><b aria-hidden="true">›</b></div>)}</nav>
    <div className="pc-nav-context"><small>SELECTED OBJECT</small><code>{cfg.selectedObject}</code><small>CONTEXT</small><code>FVT {fvt}</code><code className="good">AVAILABLE  YES</code><code className="teal">AUTHORISED YES</code><code>ACTIVE NO</code><code>MISSINGNESS 0</code></div>
    <div className="pc-nav-footer"><strong>EVIDENCE READY</strong><span>Inspector + dock synchronized</span></div>
  </aside>;
}

type InspectorRow = readonly [string,string];
function InspectorSection({title,rows}:{title:string;rows:readonly InspectorRow[]}) {
  return <section className="pc-inspector-section"><h3>{title}</h3>{rows.map(([k,v])=><div key={k}><span>{k}</span><code className={v==="YES"||v==="PASS"?"good":v.includes("12:15")?"teal":""}>{v}</code></div>)}</section>;
}

export function EvidenceInspector({ cfg }: { cfg: RouteConfig }) {
  return <aside className="pc-inspector" data-rcn-ref="production-evidence-inspector" data-figma-node="64:277" aria-label="Evidence Inspector">
    <div className="pc-inspector-head"><small>EVIDENCE INSPECTOR</small><strong>{cfg.selectedObject}</strong><b>PASS</b><span>{cfg.objectType}</span></div>
    <div className="pc-inspector-tabs"><b>SUMMARY</b><span>DETAILS</span><span>LINEAGE</span></div>
    <InspectorSection title="IDENTITY" rows={[["SOURCE",cfg.source],["GENERATION",cfg.generation],["NAMESPACE",cfg.domain==="Control"?"ovc.governance":"ovc.fixture"]]}/>
    <InspectorSection title="AUTHORITY" rows={[["AVAILABLE","YES"],["AUTHORISED","YES"],["ACTIVE","NO"],["EFFECT","NONE"]]}/>
    <InspectorSection title="CHRONOLOGY / FVT" rows={[["EFFECTIVE","12:00:00Z"],["FIRST-VALID","12:15:00Z"],["CUTOFF","12:15:00Z"]]}/>
    <InspectorSection title="MISSINGNESS" rows={[["REQUIRED","7 / 7"],["MISSING","0"],["DENOMINATOR","1,234 / 10,000"]]}/>
    <InspectorSection title="QA" rows={[["STATUS","PASS"],["ASSERTIONS","12 / 12"]]}/>
    <InspectorSection title="LINEAGE / PROVENANCE" rows={[["PARENT","C1:REC:91A"],["RUN","RUN-91"],["HASH","91a…e0c"],["SUCCESSOR","NONE"]]}/>
    <div className="pc-passport" data-figma-node="56:259">OPEN EVIDENCE PASSPORT →<small>source-bound · selection synchronized</small></div>
  </aside>;
}

export function EvidenceDock() {
  const cards = [
    ["SOURCE EVIDENCE","FIXTURE-RN-03","8,598 records · 15M/2H","investigate"],
    ["QA & COMPUTABILITY","12 / 12 PASS","5 / 5 axes evaluable","pass"],
    ["MISSINGNESS / DENOMINATOR","0 / 7 missing","sample 1,234 / universe 10,000","evidence"],
    ["CHANGE CONDITIONS","selection changes on cutoff","authority re-resolves on activation","research"],
  ];
  return <aside className="pc-dock" data-rcn-ref="production-evidence-dock" data-figma-node="65:71" aria-label="Evidence Dock"><div className="pc-dock-label"><b>EVIDENCE DOCK</b><span>selection-synchronized · source-bound</span></div><div className="pc-dock-cards">{cards.map(([title,value,detail,tone])=><article key={title} className={`pc-dock-card ${tone}`}><small>{title}</small><strong>{value}</strong><span>{detail}</span><code>source-bound</code></article>)}</div></aside>;
}

export function StatusBar() {
  return <footer className="pc-status" data-rcn-ref="production-status-bar" data-figma-node="50:316" role="status"><div><small>SYSTEM</small><strong>NOMINAL</strong></div><div><small>ENV</small><strong className="violet">RESEARCH / READ-ONLY</strong></div><div><small>DATA</small><strong className="teal">SYNTHETIC_FIXTURE · NON-EVIDENTIARY</strong></div><div><small>AUTHORITY EFFECT</small><strong>NONE</strong></div><div><small>OPERATOR</small><strong>RESEARCH_OPERATOR</strong></div></footer>;
}
