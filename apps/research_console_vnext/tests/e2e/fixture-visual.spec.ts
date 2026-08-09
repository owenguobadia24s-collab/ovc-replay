import { expect, test } from "@playwright/test";
import path from "node:path";

const screenshotRoot = path.resolve(process.cwd(), "../../artifacts/research_console_vnext/g3v_candidate_screenshots");
const viewports = [
  { name: "1920x1080", width: 1920, height: 1080, minCanvas: 420 },
  { name: "1536x864-reference", width: 1536, height: 864, minCanvas: 285 },
  { name: "1440x810", width: 1440, height: 810, minCanvas: 270 },
  { name: "1280x720", width: 1280, height: 720, minCanvas: 235 },
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
    await expect(page.getByTestId("chart-detail-hud")).toContainText("O");
    await expect(page.getByTestId("chart-detail-hud")).toContainText("H");
    await expect(page.getByTestId("chart-detail-hud")).toContainText("L");
    await expect(page.getByTestId("chart-detail-hud")).toContainText("C");
    await expect(page.locator('[data-chart-layer="reference-overlay"]')).toHaveAttribute("data-presentation-only", "true");
    const barCount = Number(await page.getByTestId("chart-bar-count").textContent());
    expect(barCount).toBeGreaterThanOrEqual(32);
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

test("WP3E reference lock reproduces the frozen 1536x864 major geometry", async ({ page }) => {
  await page.setViewportSize({ width: 1536, height: 864 });
  await page.goto("/market?investigation=FX-PROTOTYPE-01");
  const tolerance = 2.5;
  const box = async (selector: string) => {
    const value = await page.locator(selector).boundingBox();
    expect(value).not.toBeNull();
    if (!value) throw new Error(`Missing geometry for ${selector}`);
    return value;
  };
  const nav = await box('[data-rcn-ref="nav-rail"]');
  const header = await box('[data-rcn-ref="header"]');
  const contextSummary = await box('[data-rcn-ref="context-summary"]');
  const context = await box('[data-rcn-ref="context-navigator"]');
  const canvasArticle = await box('[data-rcn-ref="primary-canvas"]');
  const inspector = await box('[data-rcn-ref="evidence-inspector"]');
  const timeline = await box('[data-rcn-ref="episode-timeline"]');
  const bottom = await box('[data-rcn-ref="bottom-strip"]');
  const status = await box('[data-rcn-ref="status-bar"]');

  expect(Math.abs(nav.width - 76)).toBeLessThanOrEqual(tolerance);
  expect(Math.abs(header.height - 64)).toBeLessThanOrEqual(tolerance);
  expect(Math.abs(contextSummary.height - 60)).toBeLessThanOrEqual(tolerance);
  expect(Math.abs(status.height - 24)).toBeLessThanOrEqual(tolerance);
  expect(Math.abs(context.width - 276)).toBeLessThanOrEqual(tolerance);
  expect(Math.abs(inspector.width - 410)).toBeLessThanOrEqual(tolerance);
  expect(Math.abs(timeline.height - 140)).toBeLessThanOrEqual(3.5);
  expect(Math.abs(bottom.height - 118)).toBeLessThanOrEqual(3.5);
  expect(Math.abs(context.y - canvasArticle.y)).toBeLessThanOrEqual(1.5);
  expect(Math.abs(canvasArticle.y - inspector.y)).toBeLessThanOrEqual(1.5);
  expect(Math.abs((context.x + context.width + 6) - canvasArticle.x)).toBeLessThanOrEqual(1.5);
  expect(Math.abs((canvasArticle.x + canvasArticle.width + 6) - inspector.x)).toBeLessThanOrEqual(1.5);
});

test("WP3E keeps all bottom evidence cards on one reference baseline", async ({ page }) => {
  await page.setViewportSize({ width: 1536, height: 864 });
  await page.goto("/market?investigation=FX-PROTOTYPE-01");
  const cards = page.locator('[data-rcn-ref="bottom-strip"] > article');
  await expect(cards).toHaveCount(4);
  const boxes = await cards.evaluateAll((nodes) => nodes.map((node) => {
    const rect = node.getBoundingClientRect();
    return { y: rect.y, height: rect.height };
  }));
  const anchor = boxes[0];
  for (const current of boxes.slice(1)) {
    expect(Math.abs(current.y - anchor.y)).toBeLessThanOrEqual(1);
    expect(Math.abs(current.height - anchor.height)).toBeLessThanOrEqual(1);
  }
});

test("navigation controls cannot expose mutation semantics", async ({ page }) => {
  await page.goto("/market?investigation=FX-PROTOTYPE-01");
  const navigationOnly = page.locator('[data-navigation-only="true"]');
  await expect(navigationOnly.first()).toBeVisible();
  await navigationOnly.first().click();
  await expect(page.getByLabel("Fixture-only synchronized operator workspace")).toContainText("presentation only");
  await page.keyboard.press("Control+K");
  await expect(page.getByText("No command mutates evidence or authority.")).toBeVisible();
});
