import { useQuery } from "@tanstack/react-query";
import { NavLink, Outlet } from "react-router-dom";
import { getCapabilities, getIdentity } from "../api/client";
import { InvestigationTabs } from "../features/investigations/InvestigationTabs";
import "../design/tokens.css";
import "./foundation.css";
const nav = [["/market", "Market"], ["/structure", "Structure"], ["/research", "Research"], ["/evidence", "Evidence"], ["/control", "Control"]] as const;
export function AppShell() {
  const identity = useQuery({ queryKey: ["identity"], queryFn: getIdentity });
  const capabilities = useQuery({ queryKey: ["capabilities"], queryFn: getCapabilities });
  const sourceCommit = identity.data?.payload.commit ?? "fixture identity pending";
  const availableCount = capabilities.data?.payload.filter((item) => item.available).length ?? 0;
  return <div className="app-shell"><aside className="nav-rail" aria-label="Research Console sections"><div className="ovc-mark" aria-label="OVC">OVC</div><nav>{nav.map(([to, label]) => <NavLink key={to} to={to} className={({ isActive }) => isActive ? "nav-link is-active" : "nav-link"}>{label}</NavLink>)}</nav></aside><div className="shell-body"><header className="app-header"><div className="title-block"><strong>OVC Research Console vNext</strong><span>LOCAL · READ-ONLY</span></div><InvestigationTabs /><div className="operator-area" aria-label="Operator state">Fixture operator</div></header><div className="fixture-banner" role="status">SYNTHETIC FIXTURE · NON-EVIDENTIARY · AUTHORITY EFFECT NONE</div><div className="context-strip" aria-label="Global fixture context"><span>Source: {sourceCommit}</span><span>Available fixture capabilities: {availableCount}</span><span>Real-source routes: DENIED UNTIL RCN-G4</span></div><main className="shell-main"><Outlet /></main><footer className="status-bar"><span>RCN-WP3B prototype convergence</span><span>Fixture API only</span><span>AVAILABLE / AUTHORISED / ACTIVE remain independent</span></footer></div></div>;
}
