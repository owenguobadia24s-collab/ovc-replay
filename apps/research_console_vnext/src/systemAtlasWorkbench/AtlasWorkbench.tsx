import { useCallback, useEffect, useMemo, useState } from "react";
import { AtlasCanvas } from "./AtlasCanvas";
import { atlasProjection, projectWorkbenchQuery, relatedEdges, type AtlasNode, type AtlasSurfaceId } from "./model";
import { defaultWorkbenchState, inspectorTabs, parseWorkbenchState, serializeWorkbenchState, type AtlasWorkbenchState, type InspectorTab } from "./workbenchState";

function ResultTable({ nodes, selectedId, onSelect }: { nodes: AtlasNode[]; selectedId: string; onSelect: (id: string) => void }) {
  if (!nodes.length) return <div className="atlas-empty">No results in the bound projection.</div>;
  return (
    <div className="atlas-table-wrap">
      <table className="atlas-table">
        <thead><tr><th>Entity</th><th>Family</th><th>State</th><th>Depth</th><th>Repository source</th></tr></thead>
        <tbody>{nodes.map((node) => <tr key={node.id} className={selectedId === node.id ? "selected" : ""}><td><button onClick={() => onSelect(node.id)}>{node.label}<code>{node.id}</code></button></td><td>{node.family}</td><td><span className={`state-pill ${node.state}`}>{node.state}</span></td><td>L{node.depth}</td><td><code>{node.source.path}</code></td></tr>)}</tbody>
      </table>
    </div>
  );
}

function readPins(): string[] {
  try {
    const value: unknown = JSON.parse(window.localStorage.getItem("ovc-atlas-pins-v1") ?? "[]");
    return Array.isArray(value) && value.every((item) => typeof item === "string") ? value : [];
  } catch { return []; }
}

export function AtlasWorkbench() {
  const [state, setState] = useState<AtlasWorkbenchState>(() => parseWorkbenchState(window.location.search));
  const [copied, setCopied] = useState(false);
  const deepLink = useMemo(() => serializeWorkbenchState(state), [state]);
  const [pinned, setPinned] = useState(() => readPins().includes(deepLink));
  const update = useCallback((next: Partial<AtlasWorkbenchState>) => setState((current) => ({ ...current, ...next })), []);
  const selectNode = useCallback((id: string) => update({ selectedId: id }), [update]);
  const selected = useMemo(() => atlasProjection.nodes.find((node) => node.id === state.selectedId) ?? atlasProjection.nodes[0], [state.selectedId]);
  const surface = atlasProjection.surface_definitions.find((item) => item.id === state.surfaceId) ?? atlasProjection.surface_definitions[0];
  const result = useMemo(() => projectWorkbenchQuery({
    surfaceId: state.surfaceId,
    family: state.queryFamily,
    selectedId: state.selectedId,
    traceId: state.traceId,
    search: state.search,
  }), [state.queryFamily, state.search, state.selectedId, state.surfaceId, state.traceId]);
  const resultNodes = useMemo(() => atlasProjection.nodes.filter((node) => result.nodeIds.has(node.id)), [result]);
  const relations = relatedEdges(selected.id);
  const counts = useMemo(() => ({
    results: result.nodeIds.size,
    relations: result.edgeIds.size,
    l4: resultNodes.filter((node) => node.depth === 4).length,
    bounded: resultNodes.filter((node) => node.state === "forbidden" || node.state === "reserved").length,
  }), [result, resultNodes]);

  useEffect(() => {
    window.history.replaceState(null, "", `${window.location.pathname}${deepLink}`);
    setPinned(readPins().includes(deepLink));
  }, [deepLink]);

  const changeSurface = (surfaceId: AtlasSurfaceId) => {
    const next = defaultWorkbenchState(surfaceId);
    setState({ ...next, viewMode: state.viewMode, authorityVisible: state.authorityVisible });
  };
  const copyDeepLink = async () => {
    await navigator.clipboard.writeText(window.location.href);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1200);
  };
  const togglePin = () => {
    const pins = new Set(readPins());
    if (pins.has(deepLink)) pins.delete(deepLink); else pins.add(deepLink);
    window.localStorage.setItem("ovc-atlas-pins-v1", JSON.stringify([...pins].sort()));
    setPinned(pins.has(deepLink));
  };

  return (
    <main className="atlas-shell" data-atlas-class={atlasProjection.qualification_class}>
      <a className="skip-link" href="#atlas-content">Skip to Atlas results</a>
      <header className="atlas-header">
        <div className="atlas-brand"><span className="atlas-mark">OA</span><div><h1>OVC System Atlas</h1><p>Actual repository workbench</p></div></div>
        <div className="atlas-status"><span className="status-current">CURRENT</span><span className="status-live">LIVE SHADOW</span><span>{atlasProjection.source_tree.slice(0, 12)}</span><span>READ-ONLY</span></div>
      </header>
      <section className="atlas-toolbar" aria-label="Atlas controls">
        <label className="atlas-search"><span>SEARCH</span><input value={state.search} onChange={(event) => update({ search: event.target.value, queryFamily: "SEARCH" })} placeholder="entity, path, authority" /></label>
        <label className="atlas-query"><span>QUERY</span><select value={state.queryFamily} onChange={(event) => update({ queryFamily: event.target.value as AtlasWorkbenchState["queryFamily"] })}>{atlasProjection.query_definitions.map((query) => <option value={query.id} key={query.id}>{query.label}</option>)}</select></label>
        <label className="atlas-trace"><span>TRACE</span><select value={state.traceId} onChange={(event) => update({ traceId: event.target.value, queryFamily: "TRACE" })}><option value="whole-system">Whole system</option>{atlasProjection.traces.map((trace) => <option value={trace.id} key={trace.id}>{trace.label}</option>)}</select></label>
        <label className="atlas-toggle"><input type="checkbox" checked={state.authorityVisible} onChange={(event) => update({ authorityVisible: event.target.checked })} /><span>Authority overlay</span></label>
        <div className="atlas-metrics" aria-live="polite"><span>{counts.results} results</span><span>{counts.relations} relations</span><span>{counts.l4} L4</span><span>{counts.bounded} bounded</span></div>
      </section>
      <div className="atlas-workspace">
        <nav className="atlas-nav" aria-label="Atlas principal views">
          <h2>Principal view</h2>
          {atlasProjection.surface_definitions.map((item, index) => <button className={state.surfaceId === item.id ? "active" : ""} onClick={() => changeSurface(item.id)} key={item.id}><span>{String(index + 1).padStart(2, "0")}</span>{item.label}</button>)}
          <h2 className="query-heading">Query</h2>
          <div className="query-index">{atlasProjection.query_definitions.map((query) => <button className={state.queryFamily === query.id ? "active" : ""} onClick={() => update({ queryFamily: query.id })} key={query.id}>{query.label}</button>)}</div>
          <div className="atlas-boundary"><b>Reality</b><span>{atlasProjection.reality_class} PHYSICAL MAIN</span><b>Authority effect</b><span>{atlasProjection.presentation_state.authority_effect}</span></div>
        </nav>
        <section className="atlas-stage" id="atlas-content" aria-label="System Atlas results">
          <div className="stage-title">
            <div><span>L0-L4</span><strong>{surface.label} / {state.queryFamily}</strong></div>
            <div className="stage-actions"><div className="view-switch" role="group" aria-label="Result representation"><button className={state.viewMode === "graph" ? "active" : ""} onClick={() => update({ viewMode: "graph" })}>Graph</button><button className={state.viewMode === "table" ? "active" : ""} onClick={() => update({ viewMode: "table" })}>Table</button></div><button className="command-button" onClick={togglePin} aria-pressed={pinned} title="Pin this presentation-only view">{pinned ? "PINNED" : "PIN"}</button><button className="command-button" onClick={copyDeepLink} title="Copy typed deep link">LINK</button></div>
          </div>
          <div className="stage-results">
            {result.warning && <div className="atlas-warning" role="status">{result.warning}</div>}
            {state.viewMode === "graph" ? <AtlasCanvas visibleNodeIds={result.nodeIds} visibleEdgeIds={result.edgeIds} authorityVisible={state.authorityVisible} selectedId={selected.id} onSelect={selectNode} /> : <ResultTable nodes={resultNodes} selectedId={selected.id} onSelect={selectNode} />}
          </div>
          <div className="stage-footer"><span>POSITION / DOMAIN</span><span>SHAPE / CLASS</span><span>BORDER / AUTHORITY</span><span>OPACITY / CURRENTNESS</span><span>GRAPH = TABLE RESULT SET</span></div>
          <span className="sr-only" aria-live="polite">{copied ? "Deep link copied" : ""}</span>
        </section>
        <aside className="atlas-inspector" aria-label="Atlas Inspector">
          <div className="inspector-heading"><span>{selected.domain.toUpperCase()} / L{selected.depth}</span><h2>{selected.label}</h2><code>{selected.id}</code></div>
          <div className="inspector-tabs" role="tablist">{inspectorTabs.map((item) => <button id={`tab-${item}`} role="tab" aria-controls="atlas-inspector-panel" aria-selected={state.tab === item} className={state.tab === item ? "active" : ""} key={item} onClick={() => update({ tab: item as InspectorTab })}>{item}</button>)}</div>
          <div className="inspector-body" id="atlas-inspector-panel" role="tabpanel" aria-labelledby={`tab-${state.tab}`}>
            {state.tab === "Overview" && <dl><dt>Family</dt><dd>{selected.family}</dd><dt>State</dt><dd><span className={`state-pill ${selected.state}`}>{selected.state}</span></dd><dt>Reality class</dt><dd>{atlasProjection.reality_class}</dd><dt>Depth</dt><dd>L{selected.depth}</dd><dt>Domain</dt><dd>{selected.domain}</dd></dl>}
            {state.tab === "Relations" && <div className="relation-list">{relations.map((edge) => <button key={edge.id} onClick={() => selectNode(edge.source === selected.id ? edge.target : edge.source)}><span>{edge.family}</span><b>{edge.source === selected.id ? edge.target : edge.source}</b></button>)}</div>}
            {state.tab === "Implementation" && <dl><dt>Repository path</dt><dd className="path-value">{selected.source.path}</dd><dt>Object type</dt><dd>{selected.family}</dd><dt>Projection</dt><dd>read-only</dd></dl>}
            {state.tab === "Authority" && <dl><dt>Node state</dt><dd>{selected.state}</dd><dt>Projection effect</dt><dd>NONE</dd><dt>Console source</dt><dd>NOT BOUND</dd><dt>Publication</dt><dd>FORBIDDEN</dd></dl>}
            {state.tab === "Evidence" && <dl><dt>Git blob</dt><dd className="hash-value">{selected.source.blob}</dd><dt>Source tree</dt><dd className="hash-value">{atlasProjection.source_tree}</dd><dt>Source commit</dt><dd className="hash-value">{atlasProjection.source_commit}</dd></dl>}
            {state.tab === "History" && <dl><dt>Currentness</dt><dd>{selected.state === "historical" ? "HISTORY PLANE" : "CURRENT SOURCE TREE"}</dd><dt>Projection ID</dt><dd className="path-value">{atlasProjection.projection_id}</dd><dt>Reality</dt><dd>{atlasProjection.reality_class}</dd></dl>}
          </div>
          <div className="inspector-foot"><span>BOUND SOURCE</span><code>{selected.source.blob.slice(0, 12)}</code></div>
        </aside>
      </div>
    </main>
  );
}
