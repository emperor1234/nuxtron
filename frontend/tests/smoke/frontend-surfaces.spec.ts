import { expect, test } from "@playwright/test";

const routes = [
  "/",
  "/marketing",
  "/about",
  "/blog",
  "/blog/ai-answer-engines-are-the-new-search-results-page",
  "/blog/the-real-cost-of-the-six-tab-tax",
  "/blog/what-supervised-autonomy-means-for-ai-agents",
  "/careers",
  "/case-studies",
  "/changelog",
  "/features",
  "/pricing",
  "/integrations",
  "/contact",
  "/faq",
  "/login",
  "/register",
  "/reset-password",
  "/privacy",
  "/terms",
  "/trust",
  "/tools",
  "/tools/ai-crawler-checker",
  "/tools/agent-permission-matrix",
  "/tools/mcp-security-scanner",
  "/tools/agent-audit-log-simulator",
  "/tools/translation-studio",
  "/dashboard",
  "/seo",
  "/seo/technical",
  "/content-generation",
  "/crm",
  "/studio",
  "/studio/rank-tracker",
  "/studio/rank-tracker?tab=keyword-research",
  "/studio/backlink-intelligence",
  "/studio/avatar-builder",
  "/studio/faceless-video-engine",
  "/studio/social-studio/accounts",
  "/studio/social-studio/analytics",
  "/studio/social-studio/approvals",
  "/studio/social-studio/bulk-schedule",
  "/studio/social-studio/posts",
  "/studio/social-studio/trends",
  "/account",
  "/billing",
  "/social-listening",
];

async function getDarkHeadingContrastFailures(
  page: import("@playwright/test").Page,
) {
  return page.evaluate(() => {
    const rgb = (color: string) => {
      const values = color.match(/[\d.]+/g);
      if (!values || values.length < 3) return null;
      const [red, green, blue, alpha = "1"] = values;
      if (Number(alpha) < 0.99) return null;
      return [Number(red), Number(green), Number(blue)] as const;
    };
    const luminance = (color: readonly number[]) => {
      const channels = color.map((channel) => {
        const value = channel / 255;
        return value <= 0.04045
          ? value / 12.92
          : ((value + 0.055) / 1.055) ** 2.4;
      });
      return (
        0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]
      );
    };
    const failures: { text: string; ratio: number; background: string }[] = [];
    for (const heading of document.querySelectorAll<HTMLElement>(
      "h1, h2, h3, h4, h5, h6",
    )) {
      if (!heading.getClientRects().length) continue;
      let ancestor: HTMLElement | null = heading;
      let background: readonly number[] | null = null;
      let backgroundColor = "";
      while (ancestor) {
        const computed = getComputedStyle(ancestor).backgroundColor;
        const parsed = rgb(computed);
        if (parsed) {
          background = parsed;
          backgroundColor = computed;
          break;
        }
        ancestor = ancestor.parentElement;
      }
      if (!background || luminance(background) >= 0.35) continue;
      const foreground = rgb(getComputedStyle(heading).color);
      if (!foreground) continue;
      const foregroundLuminance = luminance(foreground);
      const backgroundLuminance = luminance(background);
      const [lighter, darker] = [
        foregroundLuminance,
        backgroundLuminance,
      ].sort((a, b) => b - a);
      const ratio = (lighter + 0.05) / (darker + 0.05);
      if (ratio < 4.5) {
        failures.push({
          text:
            heading.textContent?.trim().replace(/\s+/g, " ").slice(0, 80) ??
            "",
          ratio: Math.round(ratio * 100) / 100,
          background: backgroundColor,
        });
      }
    }
    return failures;
  });
}

for (const width of [390, 1280]) {
  test.describe(`frontend at ${width}px`, () => {
    test.use({
      viewport: { width, height: 900 },
      contextOptions: { reducedMotion: "reduce" },
    });
    for (const route of routes) {
      test(`${route} renders without page overflow`, async ({ page }) => {
        if (
          [
            "/seo",
            "/tools/ai-crawler-checker",
            "/studio/social-studio/analytics",
          ].includes(route)
        ) {
          test.setTimeout(90_000);
        }
        const pageErrors: string[] = [];
        page.on("pageerror", (error) => pageErrors.push(error.message));
        const response = await page.goto(route, {
          waitUntil: "domcontentloaded",
        });
        expect(response?.status()).toBeLessThan(400);
        await expect(page.getByRole("main").first()).toBeVisible();
        await expect(
          page.getByRole("heading", { level: 1 }).first(),
        ).toBeVisible();
        await expect(
          page.getByText("Application error: a client-side exception"),
        ).toHaveCount(0);
        expect(pageErrors).toEqual([]);
        const contrastFailures = await getDarkHeadingContrastFailures(page);
        expect(contrastFailures, `Low-contrast headings on ${route}`).toEqual(
          [],
        );
        const dimensions = await page.evaluate(() => ({
          scroll: document.documentElement.scrollWidth,
          client: document.documentElement.clientWidth,
        }));
        expect(dimensions.scroll).toBeLessThanOrEqual(dimensions.client + 1);
      });
    }
  });
}

test("Bulk Scheduler manual rows do not emit React missing-key errors", async ({
  page,
}) => {
  const reactKeyErrors: string[] = [];
  page.on("console", (message) => {
    if (
      message.type() === "error" &&
      /Each child in a list should have a unique ["']key["'] prop/i.test(
        message.text(),
      )
    ) {
      reactKeyErrors.push(message.text());
    }
  });
  await page.goto("/studio/social-studio/bulk-schedule", {
    waitUntil: "domcontentloaded",
  });
  await expect(
    page.getByRole("heading", { name: "Bulk Scheduler", level: 1 }),
  ).toBeVisible();
  await expect(page.getByPlaceholder(/Post content/).first()).toBeVisible();
  expect(reactKeyErrors).toEqual([]);
});

test("homepage demo supports keyboard use with reduced motion", async ({
  page,
}) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/");
  const tablist = page.getByRole("tablist", {
    name: /One view of search and AI visibility/,
  });
  const tabs = tablist.getByRole("tab");
  await expect(tablist).toBeVisible();
  await tabs.first().focus();
  await page.keyboard.press("ArrowRight");
  await expect(tabs.nth(1)).toHaveAttribute("aria-selected", "true");
  await expect(
    page.getByRole("tabpanel", { name: "AI visibility" }),
  ).toBeVisible();
  const playButton = page.getByRole("button", { name: "Play product tour" });
  await expect(playButton).toBeVisible();
  await expect(playButton).toHaveAttribute("aria-pressed", "false");
});

test("blog reveals honor reduced motion", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  const hydrationWarnings: string[] = [];
  page.on("console", (message) => {
    if (
      message.type() === "error" &&
      /tree hydrated|hydration/i.test(message.text())
    ) {
      hydrationWarnings.push(message.text());
    }
  });
  await page.goto("/blog", { waitUntil: "domcontentloaded" });

  const intro = page.locator(".mk-container > div").first();
  const firstPost = page.locator(".space-y-6 > div").first();
  await expect(
    page.getByRole("heading", { name: "Notes on growth, AI, and security" }),
  ).toBeVisible();
  for (const reveal of [intro, firstPost]) {
    await reveal.scrollIntoViewIfNeeded();
    await expect
      .poll(() =>
        reveal.evaluate((element) => getComputedStyle(element).opacity),
      )
      .toBe("1");
  }

  const yOffsets = await Promise.all(
    [intro, firstPost].map((reveal) =>
      reveal.evaluate((element) => {
        const transform = getComputedStyle(element).transform;
        return transform === "none" ? 0 : new DOMMatrixReadOnly(transform).m42;
      }),
    ),
  );
  expect(yOffsets).toEqual([0, 0]);
  expect(hydrationWarnings).toEqual([]);
});

test("reduced motion removes spatial hover and idle shimmer but keeps feedback", async ({
  page,
}) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/dashboard");

  const assistant = page.locator(".ira-trigger");
  await expect(assistant).toBeVisible();
  await expect
    .poll(() =>
      assistant.evaluate(
        (element) => getComputedStyle(element, "::before").content,
      ),
    )
    .toBe("none");

  const before = await assistant.evaluate((element) => {
    const style = getComputedStyle(element);
    return { boxShadow: style.boxShadow, borderColor: style.borderColor };
  });
  await assistant.hover();
  await expect
    .poll(() =>
      assistant.evaluate((element) => getComputedStyle(element).transform),
    )
    .toBe("none");
  await expect
    .poll(() =>
      assistant.evaluate((element) => getComputedStyle(element).boxShadow),
    )
    .not.toBe(before.boxShadow);
  await expect
    .poll(() =>
      assistant.evaluate((element) => getComputedStyle(element).borderColor),
    )
    .not.toBe(before.borderColor);

  await page.mouse.move(0, 0);
  await page.emulateMedia({ reducedMotion: "no-preference" });
  await assistant.hover();
  await expect
    .poll(() =>
      assistant.evaluate((element) => getComputedStyle(element).transform),
    )
    .not.toBe("none");
});

test("the shared product tour is pauseable on both product homepages", async ({
  page,
}) => {
  test.setTimeout(120_000);
  await page.emulateMedia({ reducedMotion: "no-preference" });
  for (const route of ["/", "/marketing"]) {
    await page.goto(route, { waitUntil: "domcontentloaded" });
    const surface = page.locator('[style*="--tour-step"]').first();
    await surface.scrollIntoViewIfNeeded();
    await expect(surface).toBeInViewport({ ratio: 0.35 });
    await expect
      .poll(() => page.evaluate(() => document.visibilityState))
      .toBe("visible");
    const hydrationTab = surface.getByRole("tab").nth(1);
    await expect(hydrationTab).toBeVisible();
    await hydrationTab.click();
    await expect(hydrationTab).toHaveAttribute("aria-selected", "true");

    const control = surface
      .locator(
        'button[aria-label="Pause product tour"], button[aria-label="Play product tour"]',
      )
      .first();
    await expect(control).toBeVisible();
    await expect(control).toHaveAttribute("aria-pressed", "false");
    await control.click();
    await expect(control).toHaveAttribute("aria-pressed", "true");
    await control.click();
    await expect(control).toHaveAttribute("aria-pressed", "false");
    await control.click();
    await expect(control).toHaveAttribute("aria-pressed", "true");
  }
});

test("public pages use accessible provider marks and product-specific feature previews", async ({
  page,
}) => {
  test.setTimeout(90_000);
  await page.goto("/");
  await expect(
    page.getByRole("img", { name: "ChatGPT" }).first(),
  ).toBeVisible();
  await expect(page.locator('[data-product="seo"][data-kind]')).toHaveCount(9);

  await page.goto("/marketing");
  await expect(
    page.getByRole("img", { name: "Instagram" }).first(),
  ).toBeVisible();
  await expect(
    page.locator('[data-product="marketing"][data-kind]'),
  ).toHaveCount(9);

  await page.goto("/integrations", { waitUntil: "domcontentloaded" });
  await expect(page.getByRole("img", { name: "HubSpot" })).toBeVisible();
});

test("public product films are silent, on demand, and matched to each product", async ({
  page,
}) => {
  await page.goto("/");
  const seoFilm = page.locator("video");
  await expect(seoFilm).toHaveCount(1);
  await expect(seoFilm).toHaveAttribute("controls", "");
  await expect(seoFilm).toHaveAttribute("preload", "none");
  await expect(seoFilm).not.toHaveAttribute("autoplay", "");
  await expect(seoFilm).toHaveJSProperty("muted", true);
  await expect(seoFilm.locator("source")).toHaveAttribute(
    "src",
    "/media/nuxtron-visibility-tour.mp4",
  );
  await expect(seoFilm).toHaveAttribute(
    "poster",
    "/media/nuxtron-visibility-poster.jpg",
  );
  await seoFilm.evaluate((video) => (video as HTMLVideoElement).play());
  await expect
    .poll(() =>
      seoFilm.evaluate((video) => (video as HTMLVideoElement).currentTime),
    )
    .toBeGreaterThan(0);
  await seoFilm.evaluate((video) => (video as HTMLVideoElement).pause());

  await page.goto("/marketing");
  const marketingFilm = page.locator("video");
  await expect(marketingFilm).toHaveCount(1);
  await expect(marketingFilm).toHaveAttribute("controls", "");
  await expect(marketingFilm).toHaveAttribute("preload", "none");
  await expect(marketingFilm).not.toHaveAttribute("autoplay", "");
  await expect(marketingFilm).toHaveJSProperty("muted", true);
  await expect(marketingFilm.locator("source")).toHaveAttribute(
    "src",
    "/media/nuxtron-marketing-tour.mp4",
  );
  await expect(marketingFilm).toHaveAttribute(
    "poster",
    "/media/nuxtron-marketing-poster.jpg",
  );
  await marketingFilm.evaluate((video) => (video as HTMLVideoElement).play());
  await expect
    .poll(() =>
      marketingFilm.evaluate(
        (video) => (video as HTMLVideoElement).currentTime,
      ),
    )
    .toBeGreaterThan(0);
  await marketingFilm.evaluate((video) => (video as HTMLVideoElement).pause());

  await page.goto("/features");
  await expect(page.locator("video")).toHaveCount(2);
  await page.goto("/pricing");
  await expect(page.locator("video")).toHaveCount(2);
});

test("the report-backed free tools work locally and explain their limits", async ({
  page,
}) => {
  await page.goto("/tools");
  for (const href of [
    "/tools/ai-crawler-checker",
    "/tools/agent-permission-matrix",
    "/tools/mcp-security-scanner",
    "/tools/agent-audit-log-simulator",
  ]) {
    await expect(page.locator(`a[href="${href}"]`).first()).toBeVisible();
  }

  await page.goto("/tools/ai-crawler-checker");
  await page.getByRole("button", { name: "Load example" }).click();
  await page.getByRole("button", { name: "Check crawler rules" }).click();
  await expect(
    page.getByRole("heading", { name: /Results for 10 crawler tokens/ }),
  ).toBeVisible();
  await expect(
    page.getByText("GPTBot", { exact: false }).first(),
  ).toBeVisible();
  await expect(page.getByText(/not access control/i)).toBeVisible();

  await page.goto("/tools/agent-permission-matrix");
  await page.getByLabel("Publish or send externally").check();
  await page
    .getByRole("button", { name: "Generate permission matrix" })
    .click();
  await expect(
    page.getByRole("heading", { name: "Recommended starting matrix" }),
  ).toBeVisible();
  await expect(page.getByRole("table")).toContainText(
    "Require explicit approval",
  );

  await page.goto("/tools/mcp-security-scanner");
  await page.getByRole("button", { name: "Load example" }).click();
  await page.getByRole("button", { name: "Scan configuration" }).click();
  await expect(page.getByText("No static findings detected")).toBeVisible();
  await page.getByLabel("MCP client configuration (JSON)").fill(
    JSON.stringify({
      mcpServers: {
        risky: {
          command: "bash",
          args: ["-c", "run"],
          env: { API_KEY: "secret-value-should-not-render" },
        },
      },
    }),
  );
  await page.getByRole("button", { name: "Scan configuration" }).click();
  await expect(page.getByText("Shell process configured")).toBeVisible();
  await expect(
    page.locator('[aria-labelledby="mcp-results-heading"]'),
  ).not.toContainText("secret-value-should-not-render");

  await page.goto("/tools/agent-audit-log-simulator", {
    waitUntil: "domcontentloaded",
  });
  const simulateButton = page.getByRole("button", {
    name: "Simulate audit trail",
  });
  await expect(simulateButton).toBeEnabled();
  await simulateButton.click();
  await expect(
    page.getByText("agent.action.executed", { exact: true }),
  ).toBeVisible();
  await page.getByLabel("Simulated reviewer decision").selectOption("denied");
  await simulateButton.click();
  await expect(
    page.getByText("agent.action.blocked", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("agent.action.executed", { exact: true }),
  ).toHaveCount(0);
  await expect(page.getByText(/Simulation only/).first()).toBeVisible();
});

test("public navigation no longer offers a Book a demo action", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto("/");
  await expect(page.getByRole("link", { name: /book a demo/i })).toHaveCount(0);

  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole("button", { name: "Open navigation" }).click();
  await expect(page.getByRole("link", { name: /book a demo/i })).toHaveCount(0);
  await expect(page.getByRole("link", { name: "Start free" })).toBeVisible();
});

test("workspace search restores focus after Escape", async ({ page }) => {
  await page.goto("/dashboard");
  const trigger = page.getByRole("button", { name: "Search tools and pages" });
  await trigger.click();
  await expect(
    page.getByRole("combobox", { name: "Search tools" }),
  ).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toBeHidden();
  await expect(trigger).toBeFocused();
});

test("features product-choice section heading meets contrast", async ({
  page,
}) => {
  await page.goto("/features");
  const heading = page.getByRole("heading", {
    name: "One account. Choose the product you need.",
  });
  await heading.scrollIntoViewIfNeeded();
  await expect(heading).toBeVisible();

  const ratio = await heading.evaluate((element) => {
    const section = element.closest("section");
    if (!section) throw new Error("Feature heading must have a section");
    const channels = (color: string) => {
      const values = color.match(/[\d.]+/g);
      if (!values || values.length < 3) {
        throw new Error(`Unsupported computed color: ${color}`);
      }
      return values.slice(0, 3).map(Number);
    };
    const luminance = (color: string) => {
      const [red, green, blue] = channels(color).map((channel) => {
        const normalized = channel / 255;
        return normalized <= 0.04045
          ? normalized / 12.92
          : ((normalized + 0.055) / 1.055) ** 2.4;
      });
      return 0.2126 * red + 0.7152 * green + 0.0722 * blue;
    };
    const foreground = luminance(getComputedStyle(element).color);
    const background = luminance(getComputedStyle(section).backgroundColor);
    const [lighter, darker] = [foreground, background].sort((a, b) => b - a);
    return (lighter + 0.05) / (darker + 0.05);
  });

  expect(ratio).toBeGreaterThanOrEqual(4.5);
});

test("shared product films omit redundant preview captions", async ({
  page,
}) => {
  for (const route of ["/", "/marketing", "/features", "/pricing"]) {
    await page.goto(route);
    await expect(
      page.getByText("A quick look · 8 seconds · no audio", { exact: true }),
    ).toHaveCount(0);
    await expect(
      page.getByText("Silent preview · plays on request", { exact: true }),
    ).toHaveCount(0);
  }
});
