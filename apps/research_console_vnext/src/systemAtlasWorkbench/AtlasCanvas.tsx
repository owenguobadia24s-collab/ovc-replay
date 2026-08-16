import cytoscape, { type Core, type ElementDefinition } from "cytoscape";
import { useEffect, useMemo, useRef } from "react";
import { stableAtlasPosition } from "./layout";
import { atlasProjection, nodesForTrace } from "./model";
import { atlasWorkbenchStyles } from "./styles";

type Props = {
  traceId: string;
  search: string;
  authorityVisible: boolean;
  selectedId: string;
  onSelect: (id: string) => void;
};

export function AtlasCanvas({ traceId, search, authorityVisible, selectedId, onSelect }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const instanceRef = useRef<Core | null>(null);
  const elements = useMemo<ElementDefinition[]>(() => [
    ...atlasProjection.nodes.map((node) => ({
      data: {
        id: node.id,
        label: node.label,
        domain: node.domain,
        family: node.family,
        state: node.state,
        reality: node.reality,
        depth: node.depth,
        sourcePath: node.source.path,
        sourceBlob: node.source.blob,
        compoundParent: node.parent ?? "",
      },
      position: stableAtlasPosition(node),
    })),
    ...atlasProjection.edges.map((edge) => ({ data: edge })),
  ], []);

  useEffect(() => {
    if (!containerRef.current) return undefined;
    const started = performance.now();
    const instance = cytoscape({
      container: containerRef.current,
      elements,
      style: atlasWorkbenchStyles,
      layout: { name: "preset", fit: true, padding: 34 },
      minZoom: 0.18,
      maxZoom: 3,
      boxSelectionEnabled: false,
    });
    instance.nodes().lock();
    instance.on("tap", "node", (event) => onSelect(event.target.id()));
    instanceRef.current = instance;
    containerRef.current.dataset.renderMs = (performance.now() - started).toFixed(2);
    const observer = new ResizeObserver(() => {
      instance.resize();
      instance.fit(undefined, 34);
    });
    observer.observe(containerRef.current);
    return () => { observer.disconnect(); instance.destroy(); instanceRef.current = null; };
  }, [elements, onSelect]);

  useEffect(() => {
    const instance = instanceRef.current;
    if (!instance) return;
    const traceNodes = nodesForTrace(traceId);
    const needle = search.trim().toLowerCase();
    instance.batch(() => {
      instance.elements().removeClass("trace-muted search-hit authority-hidden");
      if (traceNodes) {
        instance.nodes().forEach((node) => { if (!traceNodes.has(node.id())) node.addClass("trace-muted"); });
        instance.edges().forEach((edge) => { if (!traceNodes.has(edge.source().id()) || !traceNodes.has(edge.target().id())) edge.addClass("trace-muted"); });
      }
      if (needle) instance.nodes().filter((node) => `${node.data("label")} ${node.data("sourcePath")}`.toLowerCase().includes(needle)).addClass("search-hit");
      if (!authorityVisible) instance.elements("[family = 'authority']").addClass("authority-hidden");
      instance.$id(selectedId).select();
    });
  }, [authorityVisible, search, selectedId, traceId]);

  return <div className="atlas-canvas" ref={containerRef} data-testid="atlas-canvas" aria-label="Actual repository System Atlas graph" />;
}
