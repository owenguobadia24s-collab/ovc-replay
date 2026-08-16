import { describe, expect, it } from "vitest";
import { maxLayoutDisplacement, stableAtlasPosition } from "./layout";
import { atlasProjection, nodesForTrace } from "./model";

describe("System Atlas actual repository workbench", () => {
  it("keeps stable geography deterministic", () => {
    const first = atlasProjection.nodes.map(stableAtlasPosition);
    const second = atlasProjection.nodes.map(stableAtlasPosition);
    expect(first).toEqual(second);
    expect(maxLayoutDisplacement(atlasProjection.nodes, [...atlasProjection.nodes].reverse())).toBe(0);
  });

  it("exposes exact trace membership", () => {
    expect(nodesForTrace("market-spine")).toEqual(new Set(["opt-a", "c1", "c2", "c2e", "c2p", "esl", "c25", "c3"]));
    expect(nodesForTrace("whole-system")).toBeUndefined();
  });

  it("retains the read-only authority envelope", () => {
    expect(atlasProjection.authority_effect).toBe("NONE_PRESENTATION_ONLY");
    expect(atlasProjection.research_console_binding_created).toBe(false);
    expect(atlasProjection.current_pointer_published).toBe(false);
  });
});
