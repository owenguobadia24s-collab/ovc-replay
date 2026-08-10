import { useQuery } from "@tanstack/react-query";
import { NavLink, Outlet } from "react-router-dom";
import { getCapabilities, getIdentity, getMarketWindow, getOccurrenceContext } from "../api/client";
import { AuthorityTriad } from "../components/AuthorityTriad";
import { InvestigationTabs } from "../features/investigations/InvestigationTabs";
import "../design/tokens.css";
import "./foundation.css";
import "./wp3c-responsive.css";
import "./wp3e-reference-lock.css";
import "./wp3e-reference-polish.css";
import "./wp3f-chart-dynamics.css";

const nav = [
  ["/market", "▥", "Market Desk"],
  ["/structure", "⌘", "Structure"],
  ["/research", "♜", "Research Lab"],
  ["/evidence", "◆", "Evidence"],
  ["/control", "⌬", "Control Plane"],
] as const;

function shortClock(value?: string): string {
  if (!value) return "—";
  const match = value.match(/T(\d{2}:\d{2})/);
  return match?.[1] ?? value;
}

export function AppShell() {
  const identity = useQuery({ queryKey: ["identity"], queryFn: getIdentity });
  const capabilities = useQuery({ queryKey: ["capabilities"], queryFn: getCapabilities });
  const market = useQuery({ queryKey: ["shell-fixture-market"], queryFn: getMarketWindow });
  const context = useQuery({ queryKey: ["shell-fixture-context"], queryFn: getOccurrenceContext });
  const sourceCommit = identity.data?.payload.commit ?? "fixture-pending";
  const availableCount = capabilities.data?.payload.filter((item) => item.available).length ?? 0;
  const ctx = context.data?.payload;
  const marketCapability = market.data?.capability;
  const bars = market.data?.payload.items ?? [];
  const firstBar = bars[0];
  const lastBar = bars.at(-1);
  const period = `${shortClock(firstBar?.t)} → ${shortClock(lastBar?.t)}`;
  return <div className="app-shell" data-rcn-ref="shell">
    <aside className="nav-rail" aria-label="Research Console sections" data-rcn-ref="nav-rail">
      <div className="ovc-logo"><span>OVC</span></div>
      <nav>{nav.map(([to, icon, label]) => <NavLink key={to} to={to} className={({ isActive }) => isActive ? "nav-link is-active" : "nav-link"}><b>{icon}</b><span>{label}</span></NavLink>)}</nav>
      <div className="rail-lower"><button type="button" data-navigation-only="true"><b>⌕</b><span>Search</span></button><button type="button" data-navigation-only="true"><b>♧</b><span>Alerts</span></button><button type="button" data-navigation-only="true"><b>⚙</b><span>Settings</span></button></div>
    </aside>
    <div className="shell-body">
      <header className="app-header" data-rcn-ref="header">
        <div className="brand-block"><strong>OVC Research Console vNext</strong><span>v0.1.0 · DESIGN-ONLY</span></div>
        <InvestigationTabs />
        <div className="global-actions"><button className="search-action" type="button" data-navigation-only="true">⌕ <span>Search anything… (Ctrl+K)</span></button><button type="button" aria-label="Help" data-navigation-only="true">?</button><button type="button" aria-label="Alerts" data-navigation-only="true">♧</button><button type="button" aria-label="Theme" data-navigation-only="true">◐</button><div className="operator-chip"><b>OP</b><span>Operator</span></div></div>
      </header>
      <div className="context-summary" aria-label="Global fixture context" data-rcn-ref="context-summary">
        <div><span>INSTRUMENT</span><strong>{ctx?.instrument ?? "—"}</strong></div><div><span>CLOCK</span><strong>{ctx?.clock ?? "—"}</strong></div><div><span>SIDE</span><strong>{ctx?.side ?? "—"}</strong></div><div><span>SESSION</span><strong>{ctx?.session ?? "—"}</strong></div><div className="release-cell"><span>FIXTURE RELEASE</span><strong>{sourceCommit.slice(0, 12)}</strong></div><div><span>DATA FRESHNESS</span><strong className="freshness"><i/> Fixture current</strong></div>
        <div className="summary-authority"><AuthorityTriad available={marketCapability?.available ?? false} authorised={marketCapability?.authorised ?? false} active={marketCapability?.active ?? false} reason={`Fixture capability · ${availableCount} available`}/></div>
      </div>
      <main className="shell-main"><Outlet /></main>
      <footer className="status-bar" data-rcn-ref="status-bar"><span>CONTEXT <b>{ctx?.instrument ?? "—"} {ctx?.clock ?? "—"} {ctx?.side ?? "—"}</b></span><span>PERIOD <b>{period}</b></span><span>DATA FRESHNESS <b className="freshness"><i/> Fixture current</b></span><span>OPERATOR <b>HUMAN</b></span><span>OVC vNext <b>Design-Only</b></span><span className="fixture-status-bar" role="status">SYNTHETIC FIXTURE · NON-EVIDENTIARY · AUTHORITY EFFECT NONE · Real-source routes: DENIED UNTIL RCN-G4</span></footer>
    </div>
  </div>;
}
