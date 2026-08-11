import { expect, test, type Page } from "@playwright/test";
import { mkdirSync } from "node:fs";
import path from "node:path";

const screenshotRoot = path.resolve(process.cwd(), "../../artifacts/research_console_vnext/g3v_candidate_screenshots/figma-production");
mkdirSync(screenshotRoot, { recursive: true });

const routes = [
  ["structure", "/structure", "Investigate", "C2 structural state matrix + synchronized C2E episode rail"],
  ["research", "/research", "Research", "Representation, distance and family-stability comparison"],
  ["evidence", "/evidence", "Evidence", "Bounded lineage, dependency and QA projection"],
  ["control", "/control", "Control", "Programme state, gates, authority and dependency consequences"],
] as const;

const box = async (page: Page, selector: string) => {
  const value = await page.locator(selector).boundingBox();
  expect(value, `geometry missing for ${selector}`).not.toBeNull();
  if (!value) throw new Error(`Missing geometry for ${selector}`);
  return value;
};
const near = (actual: number, expected: number, tolerance = 1.5) => expect(Math.abs(actual - expected)).toBeLessThanOrEqual(tolerance);

async function assertTrustSpine(page: Page) {
  const shell = page.getByLabel("Fixture-only production research console");
  await expect(shell).toContainText("SYNTHETIC_FIXTURE");
  await expect(shell).toContainText("NON-EVIDENTIARY");
  await expect(shell).toContainText("AVAILABLE");
  await expect(shell).toContainText("AUTHORISED");
  await expect(shell).toContainText("ACTIVE");
  await expect(shell).toContainText("FVT");
  await expect(shell).toContainText("MISSINGNESS");
  await expect(shell).toContainText("DENOMINATOR");
  await expect(page.getByRole("status")).toContainText("AUTHORITY EFFECT");
  await expect(page.getByRole("status")).toContainText("NONE");
  await expect(page.getByRole("button", { name: /approve|activate|merge|execute|run/i })).toHaveCount(0);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)).toBe(true);
}

for (const [name, route, domain, title] of routes) {
  test(`production ${domain} master is exact at 1920x1080`, async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 });
    await page.goto(route);
    await expect(page.getByLabel("Fixture-only production research console")).toHaveAttribute("data-domain", domain);
    await expect(page.getByText(title, { exact: true })).toBeVisible();
    await assertTrustSpine(page);

    const rail = await box(page, '[data-rcn-ref="production-domain-rail"]');
    const header = await box(page, '[data-rcn-ref="production-header"]');
    const context = await box(page, '[data-rcn-ref="production-context-strip"]');
    const navigator = await box(page, '[data-rcn-ref="production-navigator"]');
    const primary = await box(page, '[data-rcn-ref="production-primary-canvas"]');
    const inspector = await box(page, '[data-rcn-ref="production-evidence-inspector"]');
    const dock = await box(page, '[data-rcn-ref="production-evidence-dock"]');
    const status = await box(page, '[data-rcn-ref="production-status-bar"]');

    near(rail.x, 0); near(rail.width, 56); near(rail.height, 1080);
    near(header.x, 56); near(header.y, 0); near(header.width, 1864); near(header.height, 56);
    near(context.x, 56); near(context.y, 56); near(context.width, 1864); near(context.height, 48);
    near(navigator.x, 56); near(navigator.y, 104); near(navigator.width, 236); near(navigator.height, 784);
    near(primary.x, 292); near(primary.y, 104); near(primary.width, 1292); near(primary.height, 784);
    near(inspector.x, 1584); near(inspector.y, 104); near(inspector.width, 320); near(inspector.height, 784);
    near(dock.x, 56); near(dock.y, 888); near(dock.width, 1864); near(dock.height, 144);
    near(status.x, 56); near(status.y, 1032); near(status.width, 1864); near(status.height, 48);

    expect(primary.width / (navigator.width + primary.width + inspector.width)).toBeGreaterThan(0.69);
    await page.screenshot({ path: path.join(screenshotRoot, `${name}-1920x1080.png`), fullPage: false });
  });
}

test("Investigate responsive master is exact at 1440x810", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 810 });
  await page.goto("/structure");
  await assertTrustSpine(page);
  const rail = await box(page, '[data-rcn-ref="production-domain-rail"]');
  const header = await box(page, '[data-rcn-ref="production-header"]');
  const context = await box(page, '[data-rcn-ref="production-context-strip"]');
  const navigator = await box(page, '[data-rcn-ref="production-navigator"]');
  const primary = await box(page, '[data-rcn-ref="production-primary-canvas"]');
  const inspector = await box(page, '[data-rcn-ref="production-evidence-inspector"]');
  const dock = await box(page, '[data-rcn-ref="production-evidence-dock"]');
  const status = await box(page, '[data-rcn-ref="production-status-bar"]');
  near(rail.width,48); near(header.x,48); near(header.height,48);
  near(context.x,48); near(context.y,48); near(context.height,42);
  near(navigator.x,48); near(navigator.y,90); near(navigator.width,200); near(navigator.height,580);
  near(primary.x,248); near(primary.y,90); near(primary.width,912); near(primary.height,580);
  near(inspector.x,1160); near(inspector.y,90); near(inspector.width,280); near(inspector.height,580);
  near(dock.x,48); near(dock.y,670); near(dock.width,1392); near(dock.height,100);
  near(status.x,48); near(status.y,770); near(status.width,1392); near(status.height,40);
  await expect(page.getByText("C2 STATE MATRIX", { exact: true })).toBeVisible();
  await expect(page.getByText("C2E EPISODE / CHRONOLOGY RAIL", { exact: true })).toBeVisible();
  await page.screenshot({ path: path.join(screenshotRoot, "structure-1440x810.png"), fullPage: false });
});

test("Investigate responsive master uses controlled inspector drawer at 1280x720", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 720 });
  await page.goto("/structure");
  await assertTrustSpine(page);
  const rail = await box(page, '[data-rcn-ref="production-domain-rail"]');
  const header = await box(page, '[data-rcn-ref="production-header"]');
  const context = await box(page, '[data-rcn-ref="production-context-strip"]');
  const navigator = await box(page, '[data-rcn-ref="production-navigator"]');
  const primary = await box(page, '[data-rcn-ref="production-primary-canvas"]');
  const inspector = await box(page, '[data-rcn-ref="production-evidence-inspector"]');
  const dock = await box(page, '[data-rcn-ref="production-evidence-dock"]');
  const status = await box(page, '[data-rcn-ref="production-status-bar"]');
  near(rail.width,48); near(header.x,48); near(header.height,48);
  near(context.x,48); near(context.y,48); near(context.height,42);
  near(navigator.x,48); near(navigator.y,90); near(navigator.width,176); near(navigator.height,500);
  near(primary.x,224); near(primary.y,90); near(primary.width,1056); near(primary.height,500);
  near(inspector.x,996); near(inspector.y,108); near(inspector.width,268); near(inspector.height,428);
  near(dock.x,48); near(dock.y,590); near(dock.width,1232); near(dock.height,90);
  near(status.x,48); near(status.y,680); near(status.width,1232); near(status.height,40);
  await expect(page.getByLabel("Evidence Inspector")).toBeVisible();
  await expect(page.getByLabel("Evidence Inspector")).toContainText("1,234 / 10,000");
  await expect(page.getByLabel("Evidence Inspector")).toContainText("12 / 12");
  await page.screenshot({ path: path.join(screenshotRoot, "structure-1280x720.png"), fullPage: false });
});

test("root enters the research-native product through Structure, not legacy Market", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveURL(/\/structure$/);
  await expect(page.getByLabel("Fixture-only production research console")).toBeVisible();
});
