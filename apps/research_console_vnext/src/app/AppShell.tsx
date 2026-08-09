import { useQuery } from "@tanstack/react-query";
import { NavLink, Outlet } from "react-router-dom";
import { getCapabilities, getIdentity, getMarketWindow, getOccurrenceContext } from "../api/client";
import { AuthorityTriad } from "../components/AuthorityTriad";
import { InvestigationTabs } from "../features/investigations/InvestigationTabs";
import "../design/tokens.css";
import "./foundation.css";

const nav = [
  ["/market", "▥", "Market Desk"],
  ["/structure", "⌘", "Structure"],
  ["/research", "♜", "Research Lab"],
  ["/evidence", "◆", "Evidence"],
  ["/control", "⌬", "Control Plane"],
] as const;

export function AppShell() {
  const identity = useQuery({ queryKey: ["identity"], queryFn: getIdentity });
  const capabilities = useQuery({ queryKey: ["capabilities"], queryFn: getCapabilities });
  const market = useQuery({ queryKey: ["shell-fixture-market"], queryFn: getMarketWindow });
  const context = useQuery({ queryKey: ["shell-fixture-context"], queryFn: getOccurrenceContext });
  const sourceCommit = identity.data?.payload.commit ?? "fixture identity pending";
  const availableCount = capabilities.data?.payload.filter((item) => item.available).length ?? 0;
  const ctx = context.data?.payload;
  const marketCapability = market.data?.capability;
  const lastBar = market.data?.payload.items.at(-1);
  return <div className="app-shell">
    <aside className="nav-rail" aria-label="Research Console sections">
      <div className="ovc-logo"><span>OVC</span></div>
      <nav>{nav.map(([to, icon, label]) => <NavLink key={to} to={to} className={({ isActive }) => isActive ? "nav-link is-active" : "nav-link"}><b>{icon}</b><span>{label}</span></NavLink>)}</nav>
      <div className="rail-lower"><button type="button" data-navigation-only="true"><b>⌕</b><span>Search</span></button><button type="button" data-navigation-only="true"><b>♧</b><span>Alerts</span></button><button type="button" data-navigation-only="true"><b>⚙</b><span>Settings</span></button></div>
    </aside>
    <div className="shell-body">
      <header className="app-header">
        <div className="brand-block"><strong>OVC Research Console vNext</strong><span>v0.1.0 · DESIGN-ONLY</span></div>
        <InvestigationTabs />
        <div className="global-actions"><button className="search-action" type="button" data-navigation-only="true">⌕ <span>Search anything… (Ctrl+K)</span></button><button type="button" aria-label="Help" data-navigation-only="true">?</button><button type="button" aria-label="Alerts" data-navigation-only="true">♧</button><button type="button" aria-label="Theme" data-navigation-only="true">◐</button><div className="operator-chip"><b>OP</b><span>Operator</span></div></div>
      </header>
      <div className="fixture-banner" role="status">SYNTHETIC FIXTURE · NON-EVIDENTIARY · AUTHORITY EFFECT NONE · Real-source routes: DENIED UNTIL RCN-G4</div>
      <div className="context-summary" aria-label="Global fixture context">
        <div><span>INSTRUMENT</span><strong>{ctx?.instrument ?? "—"}</strong></div><div><span>CLOCK</span><strong>{ctx?.clock ?? "—"}</strong></div><div><span>SIDE</span><strong>{ctx?.side ?? "—"}</strong></div><div><span>SESSION</span><strong>{ctx?.session ?? "—"}</strong></div><div className="release-cell"><span>FIXTURE SOURCE</span><strong>{sourceCommit}</strong></div><div><span>DATA FRESHNESS</span><strong className="freshness"><i/> {lastBar?.t ?? "PENDING"}</strong></div>
        <div className="summary-authority"><AuthorityTriad available={marketCapability?.available ?? false} authorised={marketCapability?.authorised ?? false} active={marketCapability?.active ?? false} reason={`Fixture capability · ${availableCount} available`}/></div>
      </div>
      <main className="shell-main"><Outlet /></main>
      <footer className="status-bar"><span>CONTEXT <b>{ctx?.instrument ?? "—"} {ctx?.clock ?? "—"} {ctx?.side ?? "—"}</b></span><span>SOURCE <b>SYNTHETIC_FIXTURE</b></span><span>OPERATOR <b>HUMAN</b></span><span>OVC vNext <b>Design-Only</b></span></footer>
    </div>
  </div>;
}
