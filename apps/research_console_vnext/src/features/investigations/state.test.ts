import { describe, expect, it } from "vitest";
import { investigationSearch, mergeLocalTabs, selectActiveInvestigation } from "./state";
import type { Investigation } from "../../api/types";
const items: Investigation[] = [{ investigation_id: "FX-BASE-01", title: "Healthy", state: "HEALTHY", fixture: true }, { investigation_id: "FX-C2E-01", title: "Inactive C2E", state: "NOT_MATERIALIZED", fixture: true }];
describe("InvestigationSet URL/local state", () => {
  it("restores requested investigation or deterministically falls back", () => { expect(selectActiveInvestigation(items, "FX-C2E-01")?.investigation_id).toBe("FX-C2E-01"); expect(selectActiveInvestigation(items, "missing")?.investigation_id).toBe("FX-BASE-01"); });
  it("keeps browser-local tabs bounded and non-duplicated", () => { expect(mergeLocalTabs(["A", "B", "C", "D", "E", "F"], "B")).toEqual(["B", "A", "C", "D", "E", "F"]); });
  it("writes active context to the URL", () => { expect(investigationSearch("FX-BASE-01").toString()).toBe("investigation=FX-BASE-01"); });
});
