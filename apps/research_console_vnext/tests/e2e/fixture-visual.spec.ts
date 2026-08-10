import { expect, test } from "@playwright/test";
import { readFileSync, writeFileSync } from "node:fs";
import path from "node:path";

const screenshotRoot = path.resolve(process.cwd(), "../../artifacts/research_console_vnext/g3v_candidate_screenshots");
const approvedReferenceB64 = readFileSync(path.resolve(process.cwd(), "tests/e2e/reference/approved-chart-reference-402x161.webp.b64"), "utf8").trim();
const viewports = [
  { name: "1920x1080", width: 1920, height: 1080, minCanvas: 420 },
  { name: "1672x941-approved-reference", width: 1672, height: 941, minCanvas: 322 },
  { name: "1536x864-reference", width: 1536, height: 864, minCanvas: 285 },
  { name: "1440x810", width: 1440, height: 810, minCanvas: 265 },
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
    await expect(canvas).toHaveAttribute("data-chart-dynamics", "wp3g");
    await expect(canvas).toHaveAttribute("data-renderer", "ovc-svg-scene");
    await expect(page.getByTestId("reference-scene")).toBeVisible();
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
    const barCount = Number(await page.getByTestId("chart-bar-count").textContent());
    expect(barCount).toBeGreaterThanOrEqual(64);
    await expect(page.locator(".wp3g-green-line")).toBeVisible();
    await expect(page.locator(".wp3g-orange-line")).toBeVisible();
    await expect(page.locator(".wp3g-blue-line")).toBeVisible();
    await expect(page.locator(".wp3g-grey-line")).toBeVisible();
    await expect(page.locator(".wp3g-marker")).toHaveCount(6);
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
    await expect(page.getByTestId("primary-canvas")).toHaveAttribute("data-renderer", "ovc-svg-scene");
    await page.screenshot({ path: path.join(screenshotRoot, `scenario-${name}-1440x810.png`), fullPage: false });
  });
}

test("WP3G measures central-scene pixel distance against the operator-approved static chart crop", async ({ page }) => {
  await page.setViewportSize({ width: 1672, height: 941 });
  await page.goto("/market?investigation=FX-PROTOTYPE-01");
  const scene = page.getByTestId("reference-scene");
  await expect(scene).toBeVisible();
  const candidateBuffer = await scene.screenshot();
  const candidateB64 = candidateBuffer.toString("base64");
  const metrics = await page.evaluate(async ({ candidateB64, approvedReferenceB64 }) => {
    const load = (src: string) => new Promise<HTMLImageElement>((resolve, reject) => {
      const image = new Image();
      image.onload = () => resolve(image);
      image.onerror = reject;
      image.src = src;
    });
    const [candidate, reference] = await Promise.all([
      load(`data:image/png;base64,${candidateB64}`),
      load(`data:image/webp;base64,${approvedReferenceB64}`),
    ]);
    const width = 402;
    const height = 161;
    const sample = (image: HTMLImageElement) => {
      const canvas = document.createElement("canvas");
      canvas.width = width;
      canvas.height = height;
      const context = canvas.getContext("2d", { willReadFrequently: true });
      if (!context) throw new Error("2D canvas unavailable");
      context.drawImage(image, 0, 0, width, height);
      return context.getImageData(0, 0, width, height).data;
    };
    const a = sample(candidate);
    const b = sample(reference);
    let total = 0;
    let different = 0;
    const pixels = width * height;
    for (let i = 0; i < a.length; i += 4) {
      const delta = (Math.abs(a[i] - b[i]) + Math.abs(a[i + 1] - b[i + 1]) + Math.abs(a[i + 2] - b[i + 2])) / (255 * 3);
      total += delta;
      if (delta > 0.14) different += 1;
    }
    return { width, height, meanRgbDistance: total / pixels, differentPixelRatio: different / pixels };
  }, { candidateB64, approvedReferenceB64 });
  writeFileSync(path.join(screenshotRoot, "wp3g-reference-pixel-metrics.json"), JSON.stringify({
    schema: "ovc-rcn-wp3g-pixel-metrics/v1",
    reference: "operator-approved static prototype chart crop, source 1672x941, crop 390,280,1195,602, downsampled 402x161",
    candidate: "OVC-owned SVG reference scene",
    ...metrics,
  }, null, 2));
  expect(metrics.meanRgbDistance).toBeLessThan(0.30);
  expect(metrics.differentPixelRatio).toBeLessThan(0.78);
});

test("WP3G owns every chart visual layer in one SVG coordinate scene", async ({ page }) => {
  await page.setViewportSize({ width: 1536, height: 864 });
  await page.goto("/market?investigation=FX-PROTOTYPE-01");
  const canvas = page.getByTestId("primary-canvas");
  await expect(canvas).toHaveAttribute("data-renderer", "ovc-svg-scene");
  await expect(page.getByTestId("reference-scene")).toHaveCount(1);
  await expect(page.locator(".wp3g-candles")).toHaveCount(1);
  await expect(page.locator(".wp3g-green-area")).toHaveCount(1);
  await expect(page.locator(".wp3g-navigator")).toHaveCount(1);
  await expect(page.locator('[data-chart-layer="reference-overlay"]')).toHaveCount(0);
});

test("WP3E shell geometry remains locked at 1536x864 around the new renderer", async ({ page }) => {
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
