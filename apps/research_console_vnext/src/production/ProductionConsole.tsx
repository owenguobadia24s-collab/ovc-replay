import { NavLink, useLocation } from "react-router-dom";
import "../design/productionTokens.css";
import "./productionConsole.css";

type Domain = "Investigate" | "Research" | "Evidence" | "Control";
type RouteConfig = {
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
  nav: readonly [string, string][];
};

const ROUTES: Record<string, RouteConfig> = {
  "/structure": {
    domain:"Investigate", kicker:"INVESTIGATE / STRUCTURE", title:"C2 structural state matrix + synchronized C2E episode rail",
    subtitle:"fixture projection · exact cutoff 16:55Z · source-bound · no reconstructed upper layer",
    navigatorTitle:"STRUCTURE / OCCURRENCE", selectedObject:"C2:OBS:8598:2417", objectType:"C2Observation",
    source:"RCN-P4-INV-STRUCT", generation:"vNext-P4", population:"8,598", instrument:"GBP/USD", clock:"15M / 2H", fvt:"2026-08-11 16:55Z",
    nav:[["Structure","214"],["Translation","8,598"],["Objects","142"],["Events","421"],["Semantics","C3"],["Chronology","FVT"]],
  },
  "/research": {
    domain:"Research", kicker:"RESEARCH / REPRESENTATIONS", title:"Representation, distance and family-stability comparison",
    subtitle:"method-first fixture · no default winner · residual / ambiguity / NO_STABLE_FAMILY are lawful",
    navigatorTitle:"REPRESENTATION / METHOD", selectedObject:"REP:R3-HYBRID-v2", objectType:"RepresentationComparison",
    source:"RCN-P4-RES-REP", generation:"SRFD-SHADOW", population:"1,240", instrument:"GBP/USD", clock:"15M / 2H", fvt:"2026-08-11 16:55Z",
    nav:[["Representations","12"],["Comparability","PAIR"],["Families","37"],["Sensitivity","6"],["Research Ops","3"],["Evaluation","A–D"]],
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
    navigatorTitle:"SYSTEM / GOVERNANCE", selectedObject:"RCN-RN-WP3E", objectType:"ProgrammeState",
    source:"MAIN@D8DA7BDF", generation:"CONTROL-V1", population:"18 PROGRAMMES", instrument:"OVC SYSTEM", clock:"REPO / UTC", fvt:"2026-08-11 16:55Z",
    nav:[["Programmes","18"],["Authority","17"],["Gates","3"],["Dependencies","42"],["Health","6"],["Repository","CLEAN"],["Orchestration","4"]],
  },
};

const domainColor = (domain: Domain) => `var(--ovc-domain-${domain.toLowerCase()})`;
const domainPath: Record<Domain,string> = { Investigate:"/structure", Research:"/research", Evidence:"/evidence", Control:"/control" };

function Rail({ domain }: { domain: Domain }) {
  return <aside className="pc-rail" data-rcn-ref="production-domain-rail" aria-label="Global domain rail">
    <div className="pc-logo">OVC</div>
    <nav>{(["Investigate","Research","Evidence","Control"] as Domain[]).map((item,index)=><NavLink key={item} to={domainPath[item]} className={item===domain?"pc-rail-link active":"pc-rail-link"} style={{"--domain":domainColor(item)} as React.CSSProperties} aria-label={item}><span>{["⌁","◇","▣","⌘"][index]}</span></NavLink>)}</nav>
    <div className="pc-rail-utils"><span>⚙</span><span>?</span></div>
  </aside>;
}

function Header({ domain }: { domain: Domain }) {
  return <header className="pc-header" data-rcn-ref="production-header">
    <div className="pc-brand"><strong>Research Console vNext</strong><small>Research operating environment</small></div>
    <nav className="pc-domain-tabs">{(["Investigate","Research","Evidence","Control"] as Domain[]).map(item=><NavLink key={item} to={domainPath[item]} className={item===domain?"active":""} style={{"--domain":domainColor(item)} as React.CSSProperties}>{item.toUpperCase()}</NavLink>)}</nav>
    <div className="pc-investigation">IROF-GOLDEN2</div>
    <div className="pc-search">⌕ <span>Search object, ID, command…</span><kbd>⌘K</kbd></div>
    <div className="pc-readonly">READ ONLY</div>
    <div className="pc-operator"><strong>RESEARCH_OPERATOR</strong><small>local · fixture-safe</small><i/></div>
  </header>;
}

function ContextStrip({ cfg }: { cfg: RouteConfig }) {
  const cells = [
    ["INSTRUMENT",cfg.instrument],["CLOCK",cfg.clock],["MODE",cfg.domain==="Control"?"READ_ONLY":"SYNTHETIC_FIXTURE"],["POPULATION",cfg.population],
    ["SOURCE",cfg.source],["GENERATION",cfg.generation],["FVT",cfg.fvt],["AVAILABLE","YES"],["AUTHORISED","YES"],["ACTIVE","NO"],["AUTHORITY EFFECT","NONE"],["FRESHNESS","FIXTURE"],
  ];
  return <div className="pc-context" data-rcn-ref="production-context-strip">{cells.map(([label,value])=><div key={label} className={`pc-context-cell ${label.toLowerCase().replace(/ /g,"-")}`}><small>{label}</small><strong>{value}</strong></div>)}</div>;
}

function Navigator({ cfg }: { cfg: RouteConfig }) {
  return <aside className="pc-navigator" data-rcn-ref="production-navigator">
    <small className="pc-domain-label" style={{color:domainColor(cfg.domain)}}>{cfg.domain.toUpperCase()}</small>
    <h2>{cfg.navigatorTitle}</h2><div className="pc-rule"/>
    <nav>{cfg.nav.map(([label,meta],index)=><div key={label} className={index===0?"pc-nav-row active":"pc-nav-row"} style={index===0?{"--domain":domainColor(cfg.domain)} as React.CSSProperties:undefined}><span>{label}</span><code>{meta}</code><b>›</b></div>)}</nav>
    <div className="pc-nav-context"><small>SELECTED OBJECT</small><code>{cfg.selectedObject}</code><small>CONTEXT</small><code>FVT {cfg.fvt.replace("2026-08-11 ","")}</code><code className="good">AVAILABLE  YES</code><code className="teal">AUTHORISED YES</code><code>MISSINGNESS 0</code></div>
    <div className="pc-nav-footer"><strong>EVIDENCE READY</strong><span>Inspector + dock synchronized</span></div>
  </aside>;
}

function EvidenceInspector({ cfg }: { cfg: RouteConfig }) {
  return <aside className="pc-inspector" data-rcn-ref="production-evidence-inspector" aria-label="Evidence Inspector">
    <div className="pc-inspector-head"><small>EVIDENCE INSPECTOR</small><strong>{cfg.selectedObject}</strong><b>PASS</b><span>{cfg.objectType}</span></div>
    <div className="pc-inspector-tabs"><b>SUMMARY</b><span>DETAILS</span><span>LINEAGE</span></div>
    <InspectorSection title="IDENTITY" rows={[["SOURCE","FIXTURE-RN-03"],["GENERATION","vNext"],["NAMESPACE","ovc.c2"]]}/>
    <InspectorSection title="AUTHORITY" rows={[["AVAILABLE","YES"],["AUTHORISED","YES"],["ACTIVE","NO"],["EFFECT","NONE"]]}/>
    <InspectorSection title="CHRONOLOGY / FVT" rows={[["EFFECTIVE","12:00:00Z"],["FIRST-VALID","12:15:00Z"],["CUTOFF","12:15:00Z"]]}/>
    <InspectorSection title="MISSINGNESS" rows={[["REQUIRED","7 / 7"],["MISSING","0"],["DENOMINATOR","1,234 / 10,000"]]}/>
    <InspectorSection title="QA" rows={[["STATUS","PASS"],["ASSERTIONS","12 / 12"]]}/>
    <InspectorSection title="LINEAGE / PROVENANCE" rows={[["PARENT","C1:REC:91A"],["RUN","RUN-91"],["HASH","91a…e0c"],["SUCCESSOR","NONE"]]}/>
    <div className="pc-passport">OPEN EVIDENCE PASSPORT →<small>source-bound · selection synchronized</small></div>
  </aside>;
}
function InspectorSection({title,rows}:{title:string;rows:string[][]}) { return <section className="pc-inspector-section"><h3>{title}</h3>{rows.map(([k,v])=><div key={k}><span>{k}</span><code className={v==="YES"||v==="PASS"?"good":v.includes("12:15")?"teal":""}>{v}</code></div>)}</section>; }

function EvidenceDock() {
  const cards = [
    ["SOURCE EVIDENCE","FIXTURE-RN-03","8,598 records · 15M/2H","investigate"],
    ["QA & COMPUTABILITY","12 / 12 PASS","5 / 5 axes evaluable","pass"],
    ["MISSINGNESS / DENOMINATOR","0 / 7 missing","sample 1,234 / universe 10,000","evidence"],
    ["CHANGE CONDITIONS","selection changes on cutoff","authority re-resolves on activation","research"],
  ];
  return <aside className="pc-dock" data-rcn-ref="production-evidence-dock" aria-label="Evidence Dock"><div className="pc-dock-label"><b>EVIDENCE DOCK</b><span>selection-synchronized · source-bound</span></div><div className="pc-dock-cards">{cards.map(([title,value,detail,tone])=><article key={title} className={`pc-dock-card ${tone}`}><small>{title}</small><strong>{value}</strong><span>{detail}</span><code>source-bound</code></article>)}</div></aside>;
}
function StatusBar() { return <footer className="pc-status" data-rcn-ref="production-status-bar" role="status"><div><small>SYSTEM</small><strong>NOMINAL</strong></div><div><small>ENV</small><strong className="violet">RESEARCH / READ-ONLY</strong></div><div><small>DATA</small><strong className="teal">SYNTHETIC_FIXTURE · NON-EVIDENTIARY</strong></div><div><small>AUTHORITY EFFECT</small><strong>NONE</strong></div><div><small>OPERATOR</small><strong>RESEARCH_OPERATOR</strong></div></footer>; }

function PrimaryHeader({cfg}:{cfg:RouteConfig}) { return <><small className="pc-primary-kicker" style={{color:domainColor(cfg.domain)}}>{cfg.kicker}</small><h1>{cfg.title}</h1><p className="pc-primary-subtitle">{cfg.subtitle}</p></>; }

const CUTS=["15:40Z","15:55Z","16:10Z","16:25Z","16:40Z","16:55Z"];
const MATRIX=[
  ["LOCATION","BELOW","RECLAIM","MID","UPPER","UPPER","RETEST"],
  ["MOTION","CONTRACT","RISING","RISING","ROTATE","FALLING","FALLING"],
  ["ORGANISATION","LOCAL","TREND","TREND","TRANSITION","RANGE","RANGE"],
  ["INTERACTION","APPROACH","TEST","CROSS","ACCEPT","REJECT","AWAY"],
  ["EVIDENCE","COMPLETE","COMPLETE","COMPLETE","COMPLETE","GAP_WARN","COMPLETE"],
];
function InvestigatePrimary({cfg}:{cfg:RouteConfig}) { return <main className="pc-primary investigate" data-testid="production-primary-canvas" data-rcn-ref="production-primary-canvas"><PrimaryHeader cfg={cfg}/><div className="pc-investigate-top"><section className="pc-panel pc-matrix"><PanelTitle title="C2 STATE MATRIX" note="Each cell is a typed source projection at its cutoff; highlighted column = selected cutoff"/><div className="pc-matrix-grid"><div/><>{CUTS.map(c=><div className={c==="16:55Z"?"cut selected":"cut"} key={c}>{c}</div>)}</>{MATRIX.map((row,r)=><div className="matrix-row-frag" key={row[0]} style={{display:"contents"}}><div className={r===4?"axis warn":"axis"}>{row[0]}</div>{row.slice(1).map((v,i)=><div key={`${r}-${i}`} className={`matrix-cell ${i===5?"selected":""} ${v==="GAP_WARN"?"warn":""}`}><code>{v}</code></div>)}</div>)}</div><div className="pc-denominator"><span>DENOMINATOR</span><b>6/6 cutoffs visible · 5 planes · 1 evidence warning · no hidden composite state</b><em>selected cutoff 16:55Z</em></div></section><section className="pc-panel pc-vector"><PanelTitle title="CURRENT STATE VECTOR" note={cfg.selectedObject}/>{[["LOCATION","RETEST"],["MOTION","FALLING"],["ORGANISATION","RANGE"],["INTERACTION","AWAY"],["EVIDENCE","COMPLETE"]].map(([a,v])=><div className="vector-row" key={a}><span>{a}</span><b className={a==="EVIDENCE"?"good":a==="MOTION"?"warn":""}>{v}</b></div>)}<hr/><small>TRANSITION LEDGER</small>{[["16:25Z","MOTION","RISING → ROTATE"],["16:40Z","INTERACTION","ACCEPT → REJECT"],["16:55Z","LOCATION","UPPER → RETEST"]].map(x=><div className="transition" key={x[0]}><code>{x[0]}</code><span>{x[1]}<b>{x[2]}</b></span></div>)}</section></div><section className="pc-panel pc-timeline"><PanelTitle title="C2E EPISODE / CHRONOLOGY RAIL" note="synchronized read-only episode context · episode identity does not rewrite C2"/><div className="timeline-events">{[["OBS","15:40Z","blue"],["PHASE","15:55Z","violet"],["OBS","16:10Z","blue"],["BOUND","16:25Z","amber"],["EVID","16:40Z","teal"],["OCC","16:55Z","teal"]].map(([a,b,c])=><div key={b} className={c}><i/><b>{a}</b><small>{b}</small></div>)}</div><div className="episode-bars"><span className="b1"/><span className="b2"/><span className="b3"/><code>BOUNDARY 16:25Z</code></div></section></main>; }

function ResearchPrimary({cfg}:{cfg:RouteConfig}) { const methods=[
  ["RAW_VECTOR","C2 frames","L1","MEDIUM","284","SHADOW"],["SEQUENCE_PATH","C2E path","DTW","HIGH","146","SHADOW"],["EVENT_HYBRID","C2+C2E","HYBRID","HIGH","119","COMPARE"],["NORM_BASE","derived","L1-W","LOW","391","BASELINE"],["AUX_ET_VS","context","MIXED","UNRESOLVED","—","MCARB"]];
  const sens=[["78%","62%","78%","0%"],["62%","78%","78%","0%"],["37%","78%","78%","62%"],["0%","62%","78%","62%"],["—","0%","62%","—"]];
  return <main className="pc-primary research" data-testid="production-primary-canvas" data-rcn-ref="production-primary-canvas"><PrimaryHeader cfg={cfg}/><div className="pc-research-top"><section className="pc-panel pc-methods"><PanelTitle title="REPRESENTATION × METHOD COMPARISON" note="same frozen parent population · independent benchmark views · fixture values illustrative"/><div className="method-head">{["METHOD","BASIS","DISTANCE","STABILITY","RESIDUAL","DISPOSITION"].map(x=><b key={x}>{x}</b>)}</div>{methods.map((row,i)=><div key={row[0]} className={`method-row ${i===2?"selected":""} ${i===4?"warn":""}`}>{row.map((v,j)=><code key={j} className={j===5&&i!==4?"good":""}>{v}</code>)}</div>)}<div className="frozen"><b>FROZEN INPUT</b><span>population 1,240 · source hash 7A91…C2 · cutoff 16:55Z · methods may compare but not rewrite parent evidence</span><em>NO METHOD SELECTOR AUTHORITY</em></div></section><section className="pc-panel pc-sensitivity"><PanelTitle title="CROSS-SENSITIVITY FAMILY SURVIVAL" note="evidence strength, not ontological truth"/><div className="sens-head"><b>R</b><b>RAW</b><b>SEQ</b><b>HYB</b><b>AUX</b></div>{sens.map((row,i)=><div className="sens-row" key={i}><code>R{["0.20","0.35","0.50","0.65","0.80"][i]}</code>{row.map((v,j)=><div key={j} className={`${v==="78%"?"positive":v==="37%"?"negative":v==="62%"?"mixed":"none"} ${i===1&&j===2?"selected":""}`}><strong>{v}</strong><small>{v==="—"?"MISSING":`${v.replace("%","")}/100`}</small></div>)}</div>)}<div className="interpret"><b>INTERPRETATION</b><span>survival = recurrence evidence only; absence may remain RESIDUAL, AMBIGUOUS or NO_STABLE_FAMILY</span></div></section></div><section className="pc-panel pc-residual"><PanelTitle title="CORRESPONDENCE / RESIDUAL CORRIDOR" note="cross-method overlap is descriptive; correspondence ≠ independence and cannot promote a winner"/>{[["INVARIANT CORE",612,"teal"],["RESIDUAL",284,"residual"],["AMBIGUOUS",104,"amber"],["NO_STABLE_FAMILY",240,"null"]].map(([label,n,tone])=><div className="residual-row" key={label as string}><span>{label}</span><div><i className={tone as string} style={{width:`${Number(n)/6.12}%`}}/></div><code>{n}</code></div>)}<div className="residual-state"><small>RESIDUAL</small><strong>Item remains outside assigned family/cohort</strong><span>No forced assignment or synthetic winner is permitted.</span></div></section></main>; }

function EvidencePrimary({cfg}:{cfg:RouteConfig}) { const nodes=[
  ["N-01","context",12,90],["N-02","related",124,38],["C2E:EP:00421","primary",260,96],["N-04","dependency",455,32],["N-05","candidate",590,86],["N-06","evidence",748,38],["N-07","context",895,98],["N-08","related",700,205],["N-09","supersession",510,230],["N-10","context",310,202],["N-11","dependency",930,215]
  ] as const; return <main className="pc-primary evidence" data-testid="production-primary-canvas" data-rcn-ref="production-primary-canvas"><PrimaryHeader cfg={cfg}/><section className="pc-panel pc-graph"><PanelTitle title="Object lineage / dependencies / QA projection" note="projection bounded · depth 2 · display_projection non-canonical"/><div className="graph-budget"><small>PROJECTION BUDGET</small><strong>214 / 50,000</strong><code>DEPTH 2</code><code>286 EDGES</code><b>BOUNDED</b><i/></div><div className="graph-legend">● Primary　● Related　◆ Candidate　● Context　■ Dependency　⬡ Evidence</div><div className="graph-stage"><svg viewBox="0 0 1010 324" aria-hidden="true"><g>{[[50,110,292,125],[155,58,292,125],[292,125,495,75],[292,125,615,105],[292,125,540,250],[540,250,325,225],[615,105,755,60],[615,105,920,110],[755,60,720,225],[720,225,945,235]].map((p,i)=><line key={i} x1={p[0]} y1={p[1]} x2={p[2]} y2={p[3]} className={i===2?"dep":i===4?"sup":"edge"}/>)}</g></svg>{nodes.map(([label,role,x,y])=><div key={label} className={`graph-node ${role}`} style={{left:x,top:y}}><i>{role==="primary"?"P":role==="related"?"R":role==="candidate"?"C":role==="dependency"?"D":role==="evidence"?"E":role==="supersession"?"S":"X"}</i><code>{label}</code></div>)}<div className="graph-selected"><small>SELECTED NODE</small><strong>C2E:EP:00421</strong><span>TYPE <code>EpisodeSnapshot</code></span><span>PARENTS <code>2</code></span><span>CHILDREN <code>3</code></span><span>FVT <code>19:15Z</code></span><span>QA <code className="good">PASS</code></span></div><div className="graph-minimap"><small>MINIMAP</small><i/><i/><i/><i/><b/></div></div><div className="graph-footer"><span>Parent　 Evidence　 QA　 Supersession　 Dependency　 Display</span><button type="button" data-navigation-only="true">⌗ DEPTH +1　<small>+187 nodes</small></button><button type="button" data-navigation-only="true">⌗ EDGE TYPE　<small>+42 edges</small></button><b>OPEN LEDGER VIEW</b></div></section><div className="pc-evidence-bottom"><section className="pc-panel qa-corridor"><PanelTitle title="QA ASSERTION CORRIDOR" note="check/version/target/status/severity/runner/commit/config/input hashes remain source-owned"/>{[["QA-DET-01","PASS","EpisodeSnapshot","qa-runner","c8a4f2","12/12"],["QA-LIN-07","PASS","LineageEdge","graph-check","c8a4f2","286 edges"],["QA-FVT-03","PASS","C2E:EP:00421","chrono","c8a4f2","FVT exact"]].map(row=><div className="qa-row" key={row[0]}>{row.map((v,i)=><code key={i} className={i===1?"good":""}>{v}</code>)}</div>)}</section><section className="pc-panel forensic"><PanelTitle title="FORENSIC SAFETY" note=""/><p><b>SOURCE RECEIPT</b><span>FIXTURE-RN-03 · hash 91A…0C · generation vNext</span></p><p><b>STALE LINK</b><span>historical object remains addressable; successor shown only when lineage exists</span></p><p><b>GRAPH LIMIT</b><span>bounded expansion · truncation explicit · no unbounded 50k request</span></p><em>IDENTITY / LINEAGE / QA reachable from selected object in ≤2 actions</em></section></div></main>; }

function ControlPrimary({cfg}:{cfg:RouteConfig}) { const programs=[
  ["RCN-RN-v0.2","WP3E","RUNNING","G3V","READ-ONLY BUILD","OPERATOR"],["C2E2-v0.2","WP5","IMPLEMENTED","G5","SHADOW","WP6"],["SFC-v0.1","WP4","RUNNING","G4","CONFORMANCE","WP5"],["SRFDI-v0.1","WP10","COMPLETED","—","COURT RECORD","ARCHIVE"],["DSAI-v0.1","WP1","COMPLETED","G1","BOOTSTRAP","WP2"],["IROF-GOLDEN2","RUN","COMPLETED","—","READ-ONLY","ARCHIVE"]];
  return <main className="pc-primary control" data-testid="production-primary-canvas" data-rcn-ref="production-primary-canvas"><PrimaryHeader cfg={cfg}/><div className="court-record"><small>COURT RECORD</small><strong>MAIN @ D8DA7BDF</strong><b>READ ONLY</b></div><div className="pc-control-top"><section className="pc-panel program-ledger"><PanelTitle title="PROGRAMME / PACKET / GATE LEDGER" note="fixture projection preserves packet identity, prerequisites and reserved authority boundaries"/><div className="program-head">{["PROGRAMME","PACKET","STATE","GATE","AUTHORITY","NEXT"].map(x=><b key={x}>{x}</b>)}</div>{programs.map((row,i)=><div className={`program-row ${i===0?"selected":""}`} key={row[0]}>{row.map((v,j)=><code key={j} className={v==="RUNNING"||v==="COMPLETED"?"good":""}>{v}</code>)}</div>)}<div className="program-foot">6 programmes visible · 1 operator-reserved gate · 0 inferred authority transitions <b>exact packet identity retained</b></div></section><section className="pc-panel authority-panel"><PanelTitle title="SELECTED PROGRAMME AUTHORITY" note="RCN-RN-v0.2 / fixture"/><div className="authority-triad"><div><small>AVAILABLE</small><b>YES</b></div><div><small>AUTHORISED</small><b>YES</b></div><div><small>ACTIVE</small><b>NO</b></div></div>{[["AVAILABLE","YES"],["AUTHORISED","YES"],["ACTIVE","NO"],["AUTHORITY EFFECT","NONE"],["RESERVED NEXT GATE","G3V · OPERATOR REQUIRED"]].map(([k,v])=><p className="authority-line" key={k}><span>{k}</span><b className={v==="YES"?"good":v.includes("OPERATOR")?"warn":""}>{v}</b></p>)}<div className="locked-state"><small>LOCKED</small><strong>Authority/protected-information boundary</strong><span>Resolution beyond the lawful envelope is denied.</span><b>INSPECT AUTHORITY →</b></div><div className="no-write"><b>NO WRITE SURFACE</b><span>approval, activation, merge and execution controls are intentionally absent</span></div></section></div><section className="pc-panel dependency-corridor"><PanelTitle title="DEPENDENCY + HEALTH CONSEQUENCE CORRIDOR" note="readiness is derived from recorded prerequisites; health signals explain consequence rather than collapsing to one score"/><div className="dependency-chain">{[["SOURCE","PASS","pass"],["CONTRACT","PASS","pass"],["FIXTURE","PASS","pass"],["QA","PASS","pass"],["GATE","LOCKED","warn"],["REAL SOURCE","DENIED","error"]].map(([a,b,c],i)=><div className="dep-frag" key={a}>{i>0&&<span>→</span>}<div className={c}><small>{a}</small><strong>{b}</strong></div></div>)}</div><p><b>CONSEQUENCE</b><span>First real-source presentation remains unavailable until the operator-reserved gate is recorded; fixture-only workbenches remain usable.</span></p><em>No destructive action · no history rewrite · no force-push · no agent write authority</em></section></main>; }

function PanelTitle({title,note}:{title:string;note:string}) { return <div className="pc-panel-title"><b>{title}</b>{note&&<small>{note}</small>}</div>; }
function Primary({cfg}:{cfg:RouteConfig}) { if(cfg.domain==="Investigate") return <InvestigatePrimary cfg={cfg}/>; if(cfg.domain==="Research") return <ResearchPrimary cfg={cfg}/>; if(cfg.domain==="Evidence") return <EvidencePrimary cfg={cfg}/>; return <ControlPrimary cfg={cfg}/>; }

export function ProductionConsole() {
  const { pathname }=useLocation(); const cfg=ROUTES[pathname] ?? ROUTES["/structure"];
  return <div className={`production-console domain-${cfg.domain.toLowerCase()}`} aria-label="Fixture-only production research console" data-domain={cfg.domain}>
    <Rail domain={cfg.domain}/><Header domain={cfg.domain}/><ContextStrip cfg={cfg}/><Navigator cfg={cfg}/><Primary cfg={cfg}/><EvidenceInspector cfg={cfg}/><EvidenceDock/><StatusBar/>
  </div>;
}
