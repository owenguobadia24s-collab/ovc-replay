import { createHash } from "node:crypto";
import { expect, test, type Page } from "@playwright/test";
import path from "node:path";

const screenshotRoot = path.resolve(process.cwd(), "../../artifacts/research_console_vnext/g3v_candidate_screenshots");
const viewports = [
  { name: "1920x1080", width: 1920, height: 1080, minMatrixHeight: 455 },
  { name: "1440x810", width: 1440, height: 810, minMatrixHeight: 295 },
  { name: "1280x720", width: 1280, height: 720, minMatrixHeight: 245 },
] as const;

async function openWorkbench(page: Page, route = "/market") {
  await page.goto(`${route}?investigation=FX-PROTOTYPE-01`);
  await expect(page.locator(".fixture-status-bar")).toContainText("SYNTHETIC FIXTURE");
  await expect(page.locator(".fixture-status-bar")).toContainText("AUTHORITY EFFECT NONE");
  await expect(page.getByRole("heading", { name: /Workbench$/ })).toBeVisible();
  await expect(page.locator(".context-summary")).toContainText("GBPUSD");
}

test("WP3E exact-head convergence contract", async ({ page }) => {
  test.setTimeout(90_000);

  for (const viewport of viewports) {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await openWorkbench(page);

    const workbench = page.getByLabel("INVESTIGATE fixture workbench");
    await expect(workbench).toHaveAttribute("data-domain", "INVESTIGATE");
    await expect(page.getByLabel("C2 MatrixView")).toBeVisible();
    await expect(page.getByLabel("C2.5 ProofTimeline")).toBeVisible();
    await expect(page.getByLabel("C3 AST Renderer")).toBeVisible();
    await expect(page.getByLabel("BoundedGraph")).toBeVisible();
    await expect(page.getByLabel("Evidence Inspector")).toBeVisible();
    await expect(page.getByLabel("Evidence Dock")).toBeVisible();
    await expect(page.locator(".rnMatrixTable tbody tr")).toHaveCount(4);
    await expect(page.getByText("NOT_EVALUABLE", { exact: true }).first()).toBeVisible();
    await expect(page.getByText("Frontend calculations: NONE", { exact: true })).toBeVisible();
    await expect(page.getByText("AUTHORITY", { exact: true }).first()).toBeVisible();
    await expect(page.getByText("NONE", { exact: true }).first()).toBeVisible();

    const matrix = await page.getByLabel("C2 MatrixView").boundingBox();
    const rows = await page.locator(".rnMatrixTable tbody tr").evaluateAll((nodes) => nodes.map((node) => {
      const rect = node.getBoundingClientRect();
      return { top: rect.top, bottom: rect.bottom };
    }));
    expect(matrix).not.toBeNull();
    expect(matrix?.height ?? 0).toBeGreaterThanOrEqual(viewport.minMatrixHeight);
    for (const row of rows) {
      expect(row.top).toBeGreaterThanOrEqual((matrix?.y ?? 0) - 1);
      expect(row.bottom).toBeLessThanOrEqual((matrix?.y ?? 0) + (matrix?.height ?? 0) + 1);
    }

    const canvas = await page.locator(".rnCanvas").boundingBox();
    const inspector = await page.getByLabel("Evidence Inspector").boundingBox();
    expect(canvas).not.toBeNull();
    expect(inspector).not.toBeNull();
    expect(Math.abs((canvas?.y ?? 0) - (inspector?.y ?? 0))).toBeLessThanOrEqual(1.5);
    expect((inspector?.x ?? 0) - ((canvas?.x ?? 0) + (canvas?.width ?? 0))).toBeLessThanOrEqual(8);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)).toBe(true);

    await page.screenshot({ path: path.join(screenshotRoot, `prototype-${viewport.name}.png`), fullPage: false });
  }

  await page.setViewportSize({ width: 1440, height: 810 });
  const routes = [
    ["/market", "INVESTIGATE"],
    ["/research", "RESEARCH"],
    ["/evidence", "EVIDENCE"],
    ["/control", "CONTROL"],
  ] as const;
  const colours = new Set<string>();
  for (const [route, domain] of routes) {
    await openWorkbench(page, route);
    const workbench = page.getByLabel(`${domain} fixture workbench`);
    await expect(workbench).toHaveAttribute("data-domain", domain);
    await expect(page.getByRole("heading", { name: `${domain} Workbench` })).toBeVisible();
    colours.add(await workbench.evaluate((node) => getComputedStyle(node).getPropertyValue("--rn-domain").trim()));
  }
  expect(colours.size).toBe(4);

  await openWorkbench(page);
  await expect(page.getByRole("button", { name: /save|publish|execute|trade|approve/i })).toHaveCount(0);
  await expect(page.locator("input:not([readonly])")).toHaveCount(0);
  await page.keyboard.press("Tab");
  const focusOutline = await page.locator(":focus").evaluate((node) => getComputedStyle(node).outlineStyle);
  expect(focusOutline).not.toBe("none");
  await expect(page.locator(".fixture-status-bar")).toContainText("Real-source routes: DENIED UNTIL RCN-G4");

  await page.setViewportSize({ width: 1920, height: 1080 });
  await openWorkbench(page);
  await page.evaluate(() => document.fonts.ready);
  const first = await page.screenshot({ animations: "disabled" });
  await page.reload();
  await expect(page.getByRole("heading", { name: "INVESTIGATE Workbench" })).toBeVisible();
  await expect(page.locator(".context-summary")).toContainText("GBPUSD");
  await page.evaluate(() => document.fonts.ready);
  const second = await page.screenshot({ animations: "disabled" });
  const hash = (buffer: Buffer) => createHash("sha256").update(buffer).digest("hex");
  expect(hash(second)).toBe(hash(first));
});
