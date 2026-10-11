import { expect, test } from "@playwright/test";

/**
 * The SEO home is built from the dashboard navigation model, so it needs no
 * backend feed to render and must never surface other vendors' product names
 * or internal engineering status to customers.
 */
test.describe("SEO home", () => {
  test("renders every SEO product section from the navigation model", async ({
    page,
  }) => {
    await page.goto("/seo");
    await expect(
      page.getByRole("heading", { name: "SEO", exact: true, level: 1 }),
    ).toBeVisible();
    for (const section of ["SEO", "AI", "Traffic", "Local"]) {
      await expect(
        page.getByRole("heading", {
          name: new RegExp(`^${section}\\b`),
          level: 2,
        }),
      ).toBeVisible();
    }
    expect(
      await page.getByTestId("seo-tool-link").count(),
    ).toBeGreaterThanOrEqual(20);
    await expect(page.getByTestId("seo-shortcut").first()).toBeVisible();
  });

  test("shows no competitor product names or internal status notes", async ({
    page,
  }) => {
    await page.goto("/seo");
    const text = await page.locator("main").innerText();
    expect(text).not.toMatch(
      /semrush|ahrefs|surfer|writesonic|botify|brightedge|hootsuite|yext|sprout social|parity|production gate|fallback active/i,
    );
  });

  test("tool links open their pages", async ({ page }) => {
    test.setTimeout(90_000);
    await page.goto("/seo");
    const siteAuditLink = page
      .getByTestId("seo-tool-link")
      .filter({ hasText: "Site Audit" })
      .first();
    await expect(siteAuditLink).toHaveAttribute("href", "/seo/technical");
    await siteAuditLink.click();
    await expect(page).toHaveURL(/\/seo\/technical$/, { timeout: 90_000 });
    await expect(
      page.getByRole("heading", { name: "Technical SEO Audit", level: 1 }),
    ).toBeVisible();
  });
});
