import cytoscape, { type ElementDefinition } from "cytoscape";
import { useEffect, useRef } from "react";
import type { AtlasLayoutResult } from "./layout";
import type { AtlasVisualGraph } from "./model";
import { atlasStyles } from "./styles";

export function toCytoscapeElements(graph: AtlasVisualGraph, layout: AtlasLayoutResult): ElementDefinition[] {
  const nodes: ElementDefinition[] = [...graph.nodes]
    .sort((left, right) => left.id.localeCompare(right.id))
    .map((node) => ({
      data: { id: node.id, label: node.label, family: node.family, state: node.state, parent: node.parent },
      position: layout.positions[node.id],
    }));
  const edges: ElementDefinition[] = [...graph.edges]
    .sort((left, right) => left.id.localeCompare(right.id))
    .map((edge) => ({ data: { id: edge.id, source: edge.source, target: edge.target, family: edge.family, state: edge.state } }));
  return [...nodes, ...edges];
}

export function AtlasFeasibilityCanvas({ graph, layout, label }: { graph: AtlasVisualGraph; layout: AtlasLayoutResult; label: string }) {
  const containerRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!containerRef.current) return undefined;
    const container = containerRef.current;
    const instance = cytoscape({
      container,
      elements: toCytoscapeElements(graph, layout),
      style: atlasStyles,
      layout: { name: "preset", fit: true, padding: 28 },
      minZoom: 0.2,
      maxZoom: 2.5,
    });
    instance.nodes().lock();
    const observer = new ResizeObserver(() => {
      instance.resize();
      instance.fit(undefined, 28);
    });
    observer.observe(container);
    return () => {
      observer.disconnect();
      instance.destroy();
    };
  }, [graph, layout]);
  return <div ref={containerRef} className="atlas-feasibility-canvas" role="img" aria-label={label} />;
}
