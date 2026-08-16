import { useCallback, useMemo, useState } from "react";
import { AtlasCanvas } from "./AtlasCanvas";
import { atlasProjection, relatedEdges } from "./model";

const tabs = ["Overview", "Relations", "Implementation", "Authority", "Evidence", "History"] as const;

export function AtlasWorkbench() {
  const [traceId, setTraceId] = useState("whole-system");
  const [search, setSearch] = useState("");
  const [authorityVisible, setAuthorityVisible] = useState(true);
  const [selectedId, setSelectedId] = useState("c2e");
  const [tab, setTab] = useState<(typeof tabs)[number]>("Overview");
  const selectNode = useCallback((id: string) => setSelectedId(id), []);
  const selected = useMemo(() => atlasProjection.nodes.find((node) => node.id === selectedId) ?? atlasProjection.nodes[0], [selectedId]);
  const relations = relatedEdges(selected.id);
  const counts = useMemo(() => ({
    nodes: atlasProjection.nodes.length,
    edges: atlasProjection.edges.length,
    authority: atlasProjection.nodes.filter((node) => node.family === "authority").length,
    restricted: atlasProjection.nodes.filter((node) => node.state === "forbidden" || node.state === "reserved").length,
  }), []);

  return (
    <main className="atlas-shell" data-atlas-class={atlasProjection.qualification_class}>
      <header className="atlas-header">
        <div className="atlas-brand"><span className="atlas-mark">OA</span><div><h1>OVC System Atlas</h1><p>ATLAS-VS0 / actual repository projection</p></div></div>
        <div className="atlas-status"><span className="status-live">LIVE SHADOW</span><span>{atlasProjection.source_tree.slice(0, 12)}</span><span>READ-ONLY</span></div>
      </header>
      <section className="atlas-toolbar" aria-label="Atlas controls">
        <label className="atlas-search"><span>SEARCH</span><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="node, path, authority" /></label>
        <label className="atlas-trace"><span>TRACE</span><select value={traceId} onChange={(event) => setTraceId(event.target.value)}><option value="whole-system">Whole system</option>{atlasProjection.traces.map((trace) => <option value={trace.id} key={trace.id}>{trace.label}</option>)}</select></label>
        <label className="atlas-toggle"><input type="checkbox" checked={authorityVisible} onChange={(event) => setAuthorityVisible(event.target.checked)} /><span>Authority overlay</span></label>
        <div className="atlas-metrics"><span>{counts.nodes} nodes</span><span>{counts.edges} relations</span><span>{counts.authority} authority</span><span>{counts.restricted} bounded</span></div>
      </section>
      <div className="atlas-workspace">
        <nav className="atlas-nav" aria-label="Atlas trace index">
          <h2>System traces</h2>
          <button className={traceId === "whole-system" ? "active" : ""} onClick={() => setTraceId("whole-system")}><span>00</span>Whole system</button>
          {atlasProjection.traces.map((trace, index) => <button className={traceId === trace.id ? "active" : ""} onClick={() => setTraceId(trace.id)} key={trace.id}><span>{String(index + 1).padStart(2, "0")}</span>{trace.label}</button>)}
          <div className="atlas-legend"><h2>State</h2><span className="current">Current</span><span className="reserved">Reserved</span><span className="historical">Historical</span><span className="forbidden">Forbidden</span></div>
          <div className="atlas-boundary"><b>Reality</b><span>{atlasProjection.qualification_class}</span><b>Authority effect</b><span>{atlasProjection.authority_effect}</span></div>
        </nav>
        <section className="atlas-stage" aria-label="System topology">
          <div className="stage-title"><div><span>L1-L4</span><strong>{traceId === "whole-system" ? "Repository topology" : atlasProjection.traces.find((trace) => trace.id === traceId)?.label}</strong></div><span className="stage-mode">STABLE GEOGRAPHY</span></div>
          <AtlasCanvas traceId={traceId} search={search} authorityVisible={authorityVisible} selectedId={selected.id} onSelect={selectNode} />
          <div className="stage-footer"><span>POSITION / DOMAIN</span><span>SHAPE / CLASS</span><span>BORDER / AUTHORITY</span><span>OPACITY / CURRENTNESS</span></div>
        </section>
        <aside className="atlas-inspector">
          <div className="inspector-heading"><span>{selected.domain.toUpperCase()} / L{selected.depth}</span><h2>{selected.label}</h2><code>{selected.id}</code></div>
          <div className="inspector-tabs" role="tablist">{tabs.map((item) => <button role="tab" aria-selected={tab === item} className={tab === item ? "active" : ""} key={item} onClick={() => setTab(item)}>{item}</button>)}</div>
          <div className="inspector-body">
            {tab === "Overview" && <dl><dt>Family</dt><dd>{selected.family}</dd><dt>State</dt><dd><span className={`state-pill ${selected.state}`}>{selected.state}</span></dd><dt>Reality class</dt><dd>{selected.reality}</dd><dt>Depth</dt><dd>L{selected.depth}</dd><dt>Domain</dt><dd>{selected.domain}</dd></dl>}
            {tab === "Relations" && <div className="relation-list">{relations.map((edge) => <button key={edge.id} onClick={() => selectNode(edge.source === selected.id ? edge.target : edge.source)}><span>{edge.family}</span><b>{edge.source === selected.id ? edge.target : edge.source}</b></button>)}</div>}
            {tab === "Implementation" && <dl><dt>Repository path</dt><dd className="path-value">{selected.source.path}</dd><dt>Object type</dt><dd>{selected.family}</dd><dt>Projection</dt><dd>read-only</dd></dl>}
            {tab === "Authority" && <dl><dt>Node state</dt><dd>{selected.state}</dd><dt>Projection effect</dt><dd>NONE</dd><dt>Console source</dt><dd>NOT BOUND</dd><dt>Publication</dt><dd>FORBIDDEN</dd></dl>}
            {tab === "Evidence" && <dl><dt>Git blob</dt><dd className="hash-value">{selected.source.blob}</dd><dt>Source tree</dt><dd className="hash-value">{atlasProjection.source_tree}</dd><dt>Source commit</dt><dd className="hash-value">{atlasProjection.source_commit}</dd></dl>}
            {tab === "History" && <dl><dt>Currentness</dt><dd>{selected.state === "historical" ? "HISTORY PLANE" : "SOURCE TREE"}</dd><dt>Projection ID</dt><dd className="path-value">{atlasProjection.projection_id}</dd></dl>}
          </div>
          <div className="inspector-foot"><span>BOUND SOURCE</span><code>{selected.source.blob.slice(0, 12)}</code></div>
        </aside>
      </div>
    </main>
  );
}
