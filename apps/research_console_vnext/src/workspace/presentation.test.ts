import { describe, expect, it } from "vitest";
import { capabilityReason, densityLabel, evidenceByKind } from "./presentation";

describe("WP3B presentation-only transforms", () => {
  it("keeps authority dimensions independent", () => {
    expect(capabilityReason({ capability_id: "C2E", available: true, authorised: true, active: false, authority_effect: "NONE" })).toBe("Capability authorised but inactive");
  });
  it("filters evidence without assigning scientific strength", () => {
    const items = [{ evidence_id: "a", kind: "SUPPORT", record_ref: "fixture:a" }, { evidence_id: "b", kind: "NULL", record_ref: "fixture:b" }];
    expect(evidenceByKind(items, "NULL").map((item) => item.evidence_id)).toEqual(["b"]);
  });
  it("uses named density modes only", () => { expect(densityLabel("dense")).toBe("Dense"); });
});
