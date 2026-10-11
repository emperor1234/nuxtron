import { expect, test } from "@playwright/test";

test("dashboard renders the marketing workspace overview", async ({ page }) => {
  await page.goto("/dashboard");

  await expect(
    page.getByRole("heading", { name: "Workspace overview" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Recent domains" }),
  ).toBeVisible();
  await expect(page.getByLabel("Website or domain")).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Analyze", exact: true }),
  ).toBeDisabled();
});

test("domain research rejects invalid input and normalizes a website URL", async ({
  page,
}) => {
  await page.goto("/dashboard");
  const domain = page.getByLabel("Website or domain");
  await domain.fill("not a domain");
  await page.getByRole("button", { name: "Analyze", exact: true }).click();
  await expect(page.locator("#domain-error")).toContainText(
    "Enter a valid domain",
  );
  await expect(domain).toBeFocused();
  await domain.fill("https://example.com/about");
  await page.getByRole("button", { name: "Analyze", exact: true }).click();
  await expect(page).toHaveURL(/\/seo\/domain-overview\?domain=example.com$/, {
    timeout: 45_000,
  });
});

test("mobile workspace navigation closes with Escape and restores focus", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/dashboard");
  const trigger = page.getByRole("button", {
    name: "Open workspace navigation",
  });
  await trigger.click();
  await expect(
    page.getByRole("dialog", { name: "Workspace navigation" }),
  ).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toBeHidden();
  await expect(trigger).toBeFocused();
});
