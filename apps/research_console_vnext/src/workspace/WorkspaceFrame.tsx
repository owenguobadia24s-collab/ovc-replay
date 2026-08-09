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
  const actions = useMemo<PaletteAction[]>(() => [
    ...DENSITY_MODES.map((mode) => ({ id: `density-${mode}`, label: `Density: ${densityLabel(mode)}`, detail: "Presentation spacing only", run: () => setDensity(mode) })),
    { id: "nav-market", label: "Open Market", detail: "Navigation only", run: () => navigate(`/market${activeId ? `?investigation=${encodeURIComponent(activeId)}` : ""}`) },
    { id: "nav-evidence", label: "Open Evidence", detail: "Navigation only", run: () => navigate(`/evidence${activeId ? `?investigation=${encodeURIComponent(activeId)}` : ""}`) },
  ], [activeId, navigate]);
  const c2Axes = c2.data?.payload.axes ?? {};
  const c2Computability = c2.data?.payload.computability ?? {};
  const c2eStatus = c2e.data?.payload.availability ?? "LOADING";
  const c2eReason = c2e.data?.payload.reason_code ?? "No reason code supplied";
  const familyNull = families.data?.payload.find((item) => item.assignment_status === "RESIDUAL");
  const capability = market.data?.capability;
  const ctx = context.data?.payload;
  const toggleLayer = (layer: string) => setLayers((current) => current.includes(layer) ? current.filter((item) => item !== layer) : [...current, layer]);
  return <section className={styles.workspace} data-density={density} aria-label="Fixture-only synchronized operator workspace">
    <CommandPalette actions={actions}/>
    <div className={styles.topGrid}>
      <aside className={styles.contextNavigator} aria-label="Context Navigator">
        <div className={styles.panelHeader}><span>A</span><strong>Context Navigator</strong></div>
        <div className={styles.investigationCard}><span>Investigation</span><strong>{activeInvestigation?.title ?? "Fixture investigation loading"}</strong><small>{activeInvestigation?.state ?? "PENDING"}</small></div>
        <dl className={styles.compactList}><div><dt>Instrument</dt><dd>{ctx?.instrument ?? "—"}</dd></div><div><dt>Clock</dt><dd>{ctx?.clock ?? "—"}</dd></div><div><dt>Side</dt><dd>{ctx?.side ?? "—"}</dd></div><div><dt>Session</dt><dd>{ctx?.session ?? "—"}</dd></div><div><dt>Source</dt><dd>SYNTHETIC_FIXTURE</dd></div></dl>
        <fieldset className={styles.layerPicker}><legend>Visible query layers</legend>{LAYERS.map((layer) => <label key={layer}><input type="checkbox" checked={layers.includes(layer)} onChange={() => toggleLayer(layer)} data-navigation-only="true"/>{layer}</label>)}</fieldset>
        <div className={styles.densityPicker} aria-label="Density mode">{DENSITY_MODES.map((mode) => <button key={mode} type="button" aria-pressed={density === mode} onClick={() => setDensity(mode)}>{densityLabel(mode)}</button>)}</div>
      </aside>
      <div className={styles.primaryColumn}>
        <article className={styles.primaryCanvas} aria-label="Primary Canvas">
          <div className={styles.panelHeader}><span>B</span><strong>Primary Canvas · Market / Structure</strong><small>{ctx?.instrument ?? "GBPUSD"} · {ctx?.clock ?? "15M"} · {ctx?.side ?? "BID"}</small></div>
          <div className={styles.coverageRow} aria-label="Structural evidence coverage">{Object.entries(c2Axes).map(([axis, value]) => <div key={axis} className={styles.coverageChip}><span>{axis}</span><strong>{value}</strong><small>{c2Computability[axis] ?? "NOT_EVALUATED"}</small></div>)}</div>
          <FixtureChart bars={bars} selectedTime={selectedTime} onSelectTime={selectTime}/>
        </article>
        <article className={styles.timeline} aria-label="C2E event timeline">
          <div className={styles.panelHeader}><span>D</span><strong>C2E Episode Timeline / Comparison Drawer</strong><small>event-sourced source only</small></div>
          <div className={styles.timelineBody}><span className={styles.timelineStatus}>{c2eStatus}</span><div className={styles.timelineTrack}><i/><b/><i/><b/></div><span>{c2eReason}</span><span>{selectedTime ? `Crosshair ${selectedTime}` : "Crosshair not selected"}</span></div>
        </article>
      </div>
      <aside className={styles.evidenceStack} aria-label="Evidence Stack">
        <div className={styles.panelHeader}><span>C</span><strong>Evidence Stack</strong></div>
        <section><h3>Object identity</h3><p>{nonEmpty(ctx?.occurrence_id, "occurrence unavailable")}</p><small>{context.data?.source_identity.commit ?? "source pending"}</small></section>
        <section><h3>Authority</h3><AuthorityTriad available={capability?.available ?? false} authorised={capability?.authorised ?? false} active={capability?.active ?? false} reason={capabilityReason(capability)}/></section>
        <section><h3>Chronology / first-valid</h3><p>{c2.data?.payload.first_valid_time ?? "NOT_MATERIALIZED"}</p></section>
        <section><h3>Availability & missingness</h3><p>C2E: {c2eStatus}</p><small>{c2eReason}</small></section>
        <section><h3>Null / residual evidence</h3><p>{familyNull?.reason_code ?? "No residual family record"}</p><small>{familyNull?.assignment_status ?? "NOT_EVALUATED"}</small></section>
        <section><h3>Evidence refs</h3>{evidenceItems.map((item) => <p key={item.evidence_id} title={item.record_ref}><strong>{item.kind}</strong> · {item.evidence_id}</p>)}</section>
      </aside>
    </div>
    <div className={styles.bottomCards}>
      <article><div className={styles.panelHeader}><span>E</span><strong>Structural Summary</strong></div><p>{Object.entries(c2Axes).map(([axis, value]) => `${axis}=${value}`).join(" · ") || "C2 fixture state loading"}</p></article>
      <article><div className={styles.panelHeader}><span>F</span><strong>Developing Episode</strong></div><p>{c2eStatus}</p><small>{c2eReason}</small></article>
      <article><div className={styles.panelHeader}><span>G</span><strong>Mini Price Context</strong></div><p>{bars.length} fixture bars · {bars.at(-1)?.c ?? "—"}</p><small>Display-only; not market evidence</small></article>
      <article><div className={styles.panelHeader}><span>H</span><strong>Support / Contradiction / Next Watch</strong></div><p>Support: {evidenceByKind(evidenceItems, "SUPPORT")[0]?.evidence_id ?? "NONE"}</p><p>Contradiction: {evidenceByKind(evidenceItems, "CONTRADICTION")[0]?.evidence_id ?? "NONE"}</p><small>Next watch: NOT_MATERIALIZED · no typed watch condition in fixture source</small></article>
    </div>
    <div className={styles.semanticFooter}>RCN-WP3B · all values are fixture-backed presentation. Coverage is not confidence. Selection, density and command actions are navigation/presentation only.</div>
  </section>;
}
