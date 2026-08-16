import cytoscape, { type Core, type ElementDefinition } from "cytoscape";
import { useEffect, useMemo, useRef } from "react";
import { stableAtlasPosition } from "./layout";
import { atlasProjection } from "./model";
import { atlasWorkbenchStyles } from "./styles";

type Props = {
  visibleNodeIds: Set<string>;
  visibleEdgeIds: Set<string>;
  authorityVisible: boolean;
  selectedId: string;
  onSelect: (id: string) => void;
};

export function AtlasCanvas({ visibleNodeIds, visibleEdgeIds, authorityVisible, selectedId, onSelect }: Props) {
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
    instance.batch(() => {
      instance.elements().removeClass("query-hidden authority-hidden");
      instance.nodes().forEach((node) => { if (!visibleNodeIds.has(node.id())) node.addClass("query-hidden"); });
      instance.edges().forEach((edge) => { if (!visibleEdgeIds.has(edge.id())) edge.addClass("query-hidden"); });
      if (!authorityVisible) instance.elements("[family = 'authority']").addClass("authority-hidden");
      instance.$id(selectedId).select();
    });
    const visible = instance.elements().not(".query-hidden").not(".authority-hidden");
    if (visible.length) instance.fit(visible, 34);
  }, [authorityVisible, selectedId, visibleEdgeIds, visibleNodeIds]);

  return <div className="atlas-canvas" ref={containerRef} data-testid="atlas-canvas" role="img" aria-label={`Actual repository System Atlas graph with ${visibleNodeIds.size} results`} />;
}
