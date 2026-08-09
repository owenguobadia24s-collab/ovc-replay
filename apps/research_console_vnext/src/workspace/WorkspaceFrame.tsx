import { useCallback, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate, useSearchParams } from "react-router-dom";
import { getC2E, getC2State, getEvidence, getFamilies, getInvestigations, getMarketWindow, getOccurrenceContext } from "../api/client";
import { AuthorityTriad } from "../components/AuthorityTriad";
import { CommandPalette, type PaletteAction } from "../components/CommandPalette";
import { FixtureChart } from "./FixtureChart";
import { DENSITY_MODES, capabilityReason, densityLabel, evidenceByKind, nonEmpty, type DensityMode } from "./presentation";
import styles from "./WorkspaceFrame.module.css";

const LAYERS = ["C2 state", "C2E lifecycle", "Evidence refs"] as const;
const AXIS_ORDER = ["location", "motion", "organisation", "interaction", "quality"] as const;
function axisLabel(value: string): string { return value.replaceAll("_", " ").replace(/\b\w/g, (m) => m.toUpperCase()); }
function shortTime(value?: string): string { if (!value) return "—"; const t = value.match(/T(\d{2}:\d{2})/); return t?.[1] ?? value; }

export function WorkspaceFrame() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [density, setDensity] = useState<DensityMode>("dense");
  const [selectedTime, setSelectedTime] = useState<string | null>(null);
  const [layers, setLayers] = useState<string[]>([...LAYERS]);
  const market = useQuery({ queryKey: ["fixture-market"], queryFn: getMarketWindow });
  const c2 = useQuery({ queryKey: ["fixture-c2"], queryFn: getC2State });
  const c2e = useQuery({ queryKey: ["fixture-c2e"], queryFn: getC2E });
  const context = useQuery({ queryKey: ["fixture-context"], queryFn: getOccurrenceContext });
  const evidence = useQuery({ queryKey: ["fixture-evidence"], queryFn: getEvidence });
  const families = useQuery({ queryKey: ["fixture-families"], queryFn: getFamilies });
  const investigations = useQuery({ queryKey: ["fixture-investigations-workspace"], queryFn: getInvestigations });
  const bars = market.data?.payload.items ?? [];
  const evidenceItems = evidence.data?.payload.items ?? [];
  const activeId = searchParams.get("investigation");
  const activeInvestigation = investigations.data?.payload.items.find((item) => item.investigation_id === activeId) ?? investigations.data?.payload.items[0];
  const selectTime = useCallback((value: string) => setSelectedTime(value), []);
  const actions = useMemo<PaletteAction[]>(() => [...DENSITY_MODES.map((mode) => ({ id: `density-${mode}`, label: `Density: ${densityLabel(mode)}`, detail: "Presentation spacing only", run: () => setDensity(mode) })), { id: "nav-market", label: "Open Market", detail: "Navigation only", run: () => navigate(`/market${activeId ? `?investigation=${encodeURIComponent(activeId)}` : ""}`) }, { id: "nav-evidence", label: "Open Evidence", detail: "Navigation only", run: () => navigate(`/evidence${activeId ? `?investigation=${encodeURIComponent(activeId)}` : ""}`) }], [activeId, navigate]);
  const c2Axes = c2.data?.payload.axes ?? {};
  const c2Computability = c2.data?.payload.computability ?? {};
  const c2eStatus = c2e.data?.payload.availability ?? "LOADING";
  const c2eReason = c2e.data?.payload.reason_code ?? "No reason code supplied";
  const familyNull = families.data?.payload.find((item) => item.assignment_status === "RESIDUAL");
  const capability = market.data?.capability;
  const ctx = context.data?.payload;
  const firstValid = c2.data?.payload.first_valid_time;
  const toggleLayer = (layer: string) => setLayers((current) => current.includes(layer) ? current.filter((item) => item !== layer) : [...current, layer]);
  const axes = AXIS_ORDER.filter((axis) => axis in c2Axes).map((axis) => [axis, c2Axes[axis], c2Computability[axis]] as const);
  return <section className={styles.workspace} data-density={density} aria-label="Fixture-only synchronized operator workspace">
    <CommandPalette actions={actions}/>
    <div className={styles.topGrid}>
      <aside className={styles.contextNavigator} aria-label="Context Navigator">
        <div className={styles.panelHeader}><span>A</span><strong>Context Navigator</strong><button type="button" data-navigation-only="true" aria-label="Collapse context">⌃</button></div>
        <div className={styles.filterBox}>⌕ <input aria-label="Filter structure tree" placeholder="Filter structure tree…" readOnly/><button type="button" data-navigation-only="true" aria-label="Filter">▽</button></div>
        <div className={styles.sectionLabel}>STRUCTURE TREE</div>
        <div className={styles.tree}>
          <div className={styles.treeRoot}>⌄ <strong>{ctx?.instrument ?? "—"} {ctx?.clock ?? "—"} {ctx?.side ?? "—"}</strong></div>
          <div className={styles.treeBranch}>⌄ {firstValid?.slice(0, 10) ?? "FIRST-VALID PENDING"}</div>
          <div className={styles.treeBranch}>⌄ {shortTime(firstValid)}</div>
          <div className={styles.selectedNode}><strong>{nonEmpty(ctx?.occurrence_id, "occurrence unavailable")}</strong><small>{activeInvestigation?.state ?? "PENDING"}</small></div>
          <div className={styles.axisList}>{axes.map(([axis, value, computability]) => <div key={axis}><i data-computable={computability === "EVALUABLE"}/><span>{axis.toUpperCase()}</span><b>{value}</b><small>{computability ?? "NOT_EVALUATED"}</small></div>)}</div>
        </div>
        <div className={styles.treePeers}>{investigations.data?.payload.items.slice(0, 4).map((item) => <div key={item.investigation_id}>› <span>{item.investigation_id}</span><small>{item.state}</small></div>)}</div>
        <div className={styles.navigatorFilters}><div className={styles.sectionLabel}>FILTERS <button type="button" data-navigation-only="true">Clear</button></div>{["Evidence Availability","Object Type","Lifecycle State","Quality State"].map((label) => <div key={label}><span>{label}</span><b>All</b><button type="button" data-navigation-only="true">⌄</button></div>)}<fieldset className={styles.layerPicker}><legend>Query layers</legend>{LAYERS.map((layer) => <label key={layer}><input type="checkbox" checked={layers.includes(layer)} onChange={() => toggleLayer(layer)} data-navigation-only="true"/>{layer}</label>)}</fieldset></div>
      </aside>

      <div className={styles.primaryColumn}>
        <article className={styles.primaryCanvas} aria-label="Primary Canvas">
          <div className={styles.canvasTabs}><span className={styles.panelBadge}>B</span><button className={styles.activeTab} type="button" data-navigation-only="true">CHART</button><button type="button" data-navigation-only="true">STRUCTURE OVERLAY</button><button type="button" data-navigation-only="true">TABLE</button><button type="button" data-navigation-only="true">COMPARISON</button></div>
          <div className={styles.canvasTitle}><div><strong>{ctx?.instrument ?? "GBPUSD"} {ctx?.clock ?? "15M"} {ctx?.side ?? "BID"}</strong><span>{firstValid ?? "FIRST-VALID NOT MATERIALIZED"} · First-Valid Time</span></div><div className={styles.canvasTools}><button type="button" data-navigation-only="true">⌁ Indicators</button><button type="button" data-navigation-only="true">⌁ Overlay</button><button type="button" data-navigation-only="true">Events</button><button type="button" data-navigation-only="true">⋮</button></div></div>
          <div className={styles.coverageLegend}><strong>Structural Evidence Coverage</strong>{axes.map(([axis, value, computability]) => <span key={axis}><i data-kind={computability ?? "NOT_EVALUATED"}/>{axisLabel(axis)}: {value}</span>)}</div>
          <FixtureChart bars={bars} selectedTime={selectedTime} onSelectTime={selectTime}/>
        </article>
        <article className={styles.timeline} aria-label="C2E event timeline">
          <div className={styles.panelHeader}><span>D</span><strong>C2E Episode Timeline</strong><small>EVENT-SOURCED SOURCE ONLY</small></div>
          <div className={styles.timelineRow}><b>E1</b><span className={styles.timelineStatus}>{c2eStatus}</span><i className={styles.birthDot}/><div className={styles.timelineTrack}><span>FIRST-VALID</span><i/><i/><i/></div><strong>{c2eReason}</strong></div>
          <div className={styles.timelineLegend}><span>● Birth</span><span>◉ Phase Mutation</span><span>⊘ Censor Gap</span><span>■ Terminate</span><span>⚡ Conflict</span><span>↳ Nest</span><span>↝ Re-Parent</span></div>
        </article>
      </div>

      <aside className={styles.evidenceStack} role="complementary" aria-label="Evidence Stack">
        <div className={styles.panelHeader}><span>C</span><strong>Evidence Inspector</strong><div className={styles.headerActions}>☆ ⧉</div></div>
        <section className={styles.identitySection}><small>OBJECT IDENTITY</small><strong>{nonEmpty(ctx?.occurrence_id, "occurrence unavailable")}</strong><span>{activeInvestigation?.state ?? "PENDING"}</span></section>
        <section><h3>Authority</h3><AuthorityTriad available={capability?.available ?? false} authorised={capability?.authorised ?? false} active={capability?.active ?? false} reason={capabilityReason(capability)}/></section>
        <section><h3>Chronology</h3><dl className={styles.inspectorList}><div><dt>First-Valid Time</dt><dd>{firstValid ?? "NOT_MATERIALIZED"}</dd></div><div><dt>Selected Time</dt><dd>{selectedTime ?? "NOT_SELECTED"}</dd></div><div><dt>Source Time (Now)</dt><dd>{bars.at(-1)?.t ?? "NOT_MATERIALIZED"}</dd></div></dl></section>
        <section><h3>Availability & Missingness</h3><div className={styles.availabilityRows}>{axes.map(([axis, value, computability]) => <div key={axis}><i data-computable={computability === "EVALUABLE"}/><span>{axis.toUpperCase()}</span><b>{value}</b></div>)}<p>C2E: <strong>{c2eStatus}</strong></p><small>{c2eReason}</small></div></section>
        <div className={styles.inspectorAccordion}>{["STRUCTURAL PAYLOAD","DEPENDENCIES","QA ASSERTIONS","LINEAGE & SUPERSESSION"].map((label) => <button key={label} type="button" data-navigation-only="true"><span>{label}</span><b>{label === "QA ASSERTIONS" ? "PASS" : "›"}</b></button>)}<button type="button" data-navigation-only="true"><span>ARTIFACT & RUN</span><b>{evidenceItems.length} refs</b></button><button type="button" data-navigation-only="true"><span>CANONICAL RAW PAYLOAD</span><b>›</b></button></div>
        <div className={styles.evidenceRefStrip}>{evidenceItems.slice(0, 4).map((item) => <span key={item.evidence_id}><strong>{item.kind}</strong> {item.evidence_id}</span>)}</div>
        <div className={styles.residualStrip}><span>NULL / RESIDUAL</span><strong>{familyNull?.reason_code ?? "No residual family record"}</strong><small>{familyNull?.assignment_status ?? "NOT_EVALUATED"}</small></div>
      </aside>
    </div>

    <div className={styles.bottomCards}>
      <article className={styles.summaryCard}><div className={styles.panelHeader}><span>E</span><strong>Structural Evidence Summary</strong></div><div className={styles.axisTiles}>{axes.slice(0,4).map(([axis, value, computability]) => <div key={axis} data-evaluable={computability === "EVALUABLE"}><small>{axis.toUpperCase()}</small><strong>{value}</strong><span>{computability ?? "NOT_EVALUATED"}</span></div>)}</div></article>
      <article><div className={styles.panelHeader}><span>F</span><strong>Developing Episode</strong></div><div className={styles.metricTiles}><div><small>START</small><strong>{shortTime(firstValid)}</strong><span>FVT</span></div><div><small>DURATION</small><strong>—</strong><span>Not materialized</span></div><div><small>STATUS</small><strong>{c2eStatus}</strong><span>C2E</span></div></div></article>
      <article><div className={styles.panelHeader}><span>G</span><strong>Price Context ({ctx?.clock ?? "—"} {ctx?.side ?? "—"})</strong></div><div className={styles.miniBars}>{bars.slice(-8).map((bar, index) => <i key={`${bar.t}-${index}`} style={{height:`${Math.max(12,Math.min(44,18+Math.abs(bar.c-bar.o)*10000))}px`}} data-up={bar.c >= bar.o}/>)}</div><small>{bars.length} fixture bars · current {bars.at(-1)?.c ?? "—"}</small></article>
      <article><div className={styles.panelHeader}><span>H</span><strong>Evidence & Change Conditions</strong></div><div className={styles.conditionGrid}><div><small>SUPPORT</small><strong>{evidenceByKind(evidenceItems, "SUPPORT")[0]?.evidence_id ?? "NONE"}</strong><span>Fixture evidence ref</span></div><div><small>CONTRADICTION</small><strong>{evidenceByKind(evidenceItems, "CONTRADICTION")[0]?.evidence_id ?? "NONE"}</strong><span>Fixture evidence ref</span></div><div><small>NEXT WATCH</small><strong>NOT_MATERIALIZED</strong><span>No typed watch condition in fixture source</span></div></div></article>
    </div>
    <div className={styles.semanticFooter}>RCN-WP3C · fixture-backed visual convergence remediation · Coverage is not confidence · selection, filters, density and command actions are presentation only.</div>
  </section>;
}
