import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { getInvestigations } from "../../api/client";
import type { Investigation } from "../../api/types";
import { queryClient } from "../../app/queryClient";
import { INVESTIGATION_EVIDENCE_CLASS, INVESTIGATION_QUERY_KEY, LOCAL_TAB_STORAGE_KEY, mergeLocalTabs, selectActiveInvestigation } from "./state";

function readStoredTabs(): string[] { try { const raw = window.localStorage.getItem(LOCAL_TAB_STORAGE_KEY); const parsed = raw ? JSON.parse(raw) : []; return Array.isArray(parsed) && parsed.every((value) => typeof value === "string") ? parsed : []; } catch { return []; } }

export function InvestigationTabs() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [openIds, setOpenIds] = useState<string[]>(readStoredTabs);
  const investigationsQuery = useQuery({ queryKey: ["fixture-investigations"], queryFn: getInvestigations });
  const items = investigationsQuery.data?.payload.items ?? [];
  const requested = searchParams.get(INVESTIGATION_QUERY_KEY);
  const active = useMemo(() => selectActiveInvestigation(items, requested), [items, requested]);
  useEffect(() => { if (!active) return; if (requested !== active.investigation_id) { const next = new URLSearchParams(searchParams); next.set(INVESTIGATION_QUERY_KEY, active.investigation_id); setSearchParams(next, { replace: true }); } const nextIds = mergeLocalTabs(openIds, active.investigation_id); if (nextIds.join("|") !== openIds.join("|")) { setOpenIds(nextIds); window.localStorage.setItem(LOCAL_TAB_STORAGE_KEY, JSON.stringify(nextIds)); } }, [active, openIds, requested, searchParams, setSearchParams]);
  const openItems = openIds.map((id) => items.find((item) => item.investigation_id === id)).filter((item): item is Investigation => Boolean(item));
  const visible = openItems.length ? openItems : items.slice(0, 3);
  async function activate(item: Investigation): Promise<void> { const next = new URLSearchParams(searchParams); next.set(INVESTIGATION_QUERY_KEY, item.investigation_id); setSearchParams(next); setOpenIds((current) => { const updated = mergeLocalTabs(current, item.investigation_id); window.localStorage.setItem(LOCAL_TAB_STORAGE_KEY, JSON.stringify(updated)); return updated; }); await Promise.all([queryClient.invalidateQueries({ queryKey: ["identity"] }), queryClient.invalidateQueries({ queryKey: ["capabilities"] }), queryClient.invalidateQueries({ queryKey: ["fixture-investigations"] })]); }
  if (investigationsQuery.isPending) return <div className="investigation-tabs">Loading fixture investigations…</div>;
  if (investigationsQuery.isError) return <div className="investigation-tabs">Fixture investigation source unavailable.</div>;
  return <div className="investigation-tabs" role="tablist" aria-label={`Synthetic fixture investigations · ${INVESTIGATION_EVIDENCE_CLASS}`}>{visible.map((item) => <button key={item.investigation_id} type="button" role="tab" aria-selected={item.investigation_id === active?.investigation_id} className={item.investigation_id === active?.investigation_id ? "investigation-tab is-active" : "investigation-tab"} onClick={() => void activate(item)}><span>{item.title}</span><small>{item.state}</small></button>)}<button type="button" className="new-investigation-tab" disabled aria-disabled="true" title="Creation remains outside fixture-only read authority">＋ New Investigation</button></div>;
}
