import { expect, test } from "@playwright/test";
import path from "node:path";

const screenshotRoot = path.resolve(process.cwd(), "../../artifacts/research_console_vnext/g3v_candidate_screenshots");
const viewports = [
  { name: "1920x1080", width: 1920, height: 1080, minCanvas: 420 },
  { name: "1440x810", width: 1440, height: 810, minCanvas: 300 },
  { name: "1280x720", width: 1280, height: 720, minCanvas: 260 },
] as const;

for (const viewport of viewports) {
  test(`prototype fixture ${viewport.name} preserves the governed canvas and labels`, async ({ page }) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await page.goto("/market?investigation=FX-PROTOTYPE-01");
    await expect(page.getByRole("status")).toContainText("SYNTHETIC FIXTURE");
    await expect(page.getByRole("status")).toContainText("NON-EVIDENTIARY");
    const canvas = page.getByTestId("primary-canvas");
    await expect(canvas).toBeVisible();
    await expect.poll(async () => (await canvas.boundingBox())?.height ?? 0).toBeGreaterThanOrEqual(viewport.minCanvas);
    const evidenceStack = page.getByRole("complementary", { name: "Evidence Stack" });
    await expect(evidenceStack).toContainText("C2E: NOT_MATERIALIZED");
    await expect(evidenceStack).toContainText("AVAILABLE");
    await expect(evidenceStack).toContainText("AUTHORISED");
    await expect(evidenceStack).toContainText("ACTIVE");
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)).toBe(true);
    await page.screenshot({ path: path.join(screenshotRoot, `prototype-${viewport.name}.png`), fullPage: false });
  });
}

const scenarios = [
  ["healthy", "FX-BASE-01", "HEALTHY"],
  ["inactive-c2e", "FX-C2E-01", "NOT_MATERIALIZED"],
  ["null-residual", "FX-RSCH-02", "NO_STABLE_FAMILY"],
  ["authority-denied", "FX-GOV-01", "AUTHORITY_DENIED"],
  ["dense", "FX-DENSITY-01", "DENSE_SYNTHETIC"],
] as const;

for (const [name, investigation, expectedState] of scenarios) {
  test(`G3V scenario ${name} remains explicit and non-evidentiary`, async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 810 });
    await page.goto(`/market?investigation=${investigation}`);
    await expect(page.getByRole("status")).toContainText("AUTHORITY EFFECT NONE");
    await expect(page.getByText(expectedState, { exact: true }).first()).toBeVisible();
    await expect(page.getByLabel("Fixture-only synchronized operator workspace")).toContainText("Coverage is not confidence");
    await page.screenshot({ path: path.join(screenshotRoot, `scenario-${name}-1440x810.png`), fullPage: false });
  });
}

test("navigation controls cannot expose mutation semantics", async ({ page }) => {
  await page.goto("/market?investigation=FX-PROTOTYPE-01");
  const navigationOnly = page.locator('[data-navigation-only="true"]');
  await expect(navigationOnly.first()).toBeVisible();
  await navigationOnly.first().click();
  await expect(page.getByLabel("Fixture-only synchronized operator workspace")).toContainText("presentation only");
  await page.keyboard.press("Control+K");
  await expect(page.getByText("No command mutates evidence or authority.")).toBeVisible();
});
