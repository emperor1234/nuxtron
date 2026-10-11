# Frontend redesign

Scope: all public and authenticated routes, preserving existing functionality and pre-existing working-tree changes.

Direction: warm neutral canvas, dark ink, the original Nuxtron blue accent, consistent Geist typography, clear navigation, honest data states. Homepage motion explains a workflow and respects reduced motion. Frequent product interactions stay immediate.

## Work

- [x] Inspect architecture, authentication, route navigation, shared UI, public pages and reference content.
- [x] Unify global, marketing and product tokens; repair shared controls and responsive foundations.
- [x] Rebuild homepage and shared public navigation; simplify authentication surfaces.
- [x] Rebuild product navigation and workspace overview with honest partial-error states.
- [x] Migrate legacy route styling and remove decorative product effects.
  - Replaced the dark-theme palette left behind on light product surfaces (Studio workspace, Social Studio) which rendered near-white text on near-white panels.
  - Moved every off-system colour on 30+ routes onto the shared tokens; platform brand colours and illustration fills stay literal.
  - Dropped the cyan/pink marketing gradients and quarantined ten unused imported-template components to `junk/dead-ui/`.
- [x] Verify types, focused unit tests, browser smoke tests and route coverage.
  - Current checks: TypeScript clean, 182 unit tests pass, contrast script reports no pair below 4.5:1.
  - Chrome route and interaction checks were completed at mobile and desktop widths; cold compilation and a tour-test selector issue were corrected and individually reverified below.

## Verification limits

The in-app browser runtime reported no available browsers. Project Playwright tests remain available for automated checks; interactive visual inspection must not be claimed unless a browser connection becomes available.

## Dual-product homepage and product split (2026-10-09)

- `/` is the Nuxtron SEO homepage, `/marketing` the Nuxtron Marketing homepage. Both render `app/(public)/_components/sections/homepage.tsx` with data from `app/(public)/_content/{seo,marketing}.ts` (contract: `_content/types.ts`).
- Sign-in mode: `?product=` from the switch bar → product picker on /login and /register → httpOnly `nuxtron_product` cookie via `/api/auth/session` → `proxy.ts` redirects the other product's routes to `/dashboard?unavailable=<product>`. Route ownership comes from `product` on each rail item in `_shell/nav.ts` (see `app/lib/product-line.ts`). Operations, Home and Settings are shared.
- It is a mode, not an entitlement. A backend `product` JWT claim, if issued, takes precedence over the cookie.
- Proof carousel and trust badges render nothing until verified entries (with a checkable source/URL) are added to the content files. Never placeholder.
- Hero engine list = engines `backend/fastapi/app/answer_engine/insights.py` actually queries. Do not add Google AI Overviews or Copilot there: they are scoring targets only.
- Verified: typecheck, 150 unit tests, lint on all touched files, production build, 73 browser checks at 1440/390, 17 end-to-end proxy enforcement checks with a throwaway signing key.

## Public brand, motion and navigation pass (2026-10-10)

### Reference research

- [Semrush](https://www.semrush.com/) — a clear visibility promise and direct next step near the top. Applied as concise, product-specific Nuxtron messaging and a low-friction action, without borrowing Semrush copy or visual assets.
- [HubSpot](https://www.hubspot.com/) and its [navigation guide](https://knowledge.hubspot.com/help-and-resources/a-guide-to-hubspots-navigation) — grouped product areas and predictable destinations. Applied by keeping Nuxtron's SEO/Marketing split, typed workspace navigation, global route search and internal-tool guardrails.
- [Profound](https://www.tryprofound.com/) — a focused AI-visibility story supported by product evidence close to the top. Applied with Nuxtron-owned product films and the existing interactive Nuxtron walkthrough, not Profound copy, UI, logos or customer proof.

### Changes

- Added separate, self-hosted 8-second Nuxtron SEO and Nuxtron Marketing motion films. The related-film component appears on both product homepages, the filtered feature directory and pricing. Playback is muted, controlled, non-autoplaying and `preload="none"`, with optimized product-specific posters.
- Standardized the existing Nuxtron NX mark across the marketing header/footer, dashboard rail and product mockups; updated the PWA icon/manifest, browser theme color, Open Graph artwork and generated Open Graph fallback to the original blue Nuxtron identity.
- Made the dashboard's current rail section explicit to assistive technology, restored keyboard focus to the search entry point after closing its command palette, and added navigation coverage preventing third-party product-branded internal routes from leaking into customer discovery. Vendor-specific internal consoles remain internal; factual provider marks identify real coverage without implying affiliation.
- Preserved the existing animated dashboard and interactive tour; motion remains product-explanatory, user-controllable and responsive to reduced-motion preferences. Darkened the shared strong scrim after the contrast audit found a 4.43:1 overlay label; the final audit reports no foreground/background pairs below 4.5:1.

### Verification

- TypeScript: passed.
- Contrast audit: passed, 0 pairs below 4.5:1.
- Focused ESLint on changed application source: passed; newly added component files also pass Prettier.
- Unit tests: 21 files, 166 tests passed.
- Focused Playwright surface coverage: 35 route/video checks passed, including muted user-triggered playback of both videos; the two keyboard/focus interactions were corrected and each passed a follow-up Chrome run. The initial full surface run used the system Google Chrome because the Playwright-managed Chromium binary is not installed on this device.
- The repository-wide lint command is still blocked by thousands of existing errors in unrelated files; the changed application source passes focused lint. A whole-tree whitespace scan also finds three pre-existing trailing-space lines in the Studio workspace; the task-scoped diff passes `git diff --check`.


## Provider marks, restored blue, and capability previews (2026-10-11)

- Restored the original Nuxtron blue (`#2563c9`) and cyan (`#22cdea`) while retaining warm-neutral surfaces. The Nuxtron-owned NX icon and wordmark remain distinct from provider marks; browser/PWA theming follows the same blue.
- Added a locally served registry of 28 third-party provider marks with normalization for product names and common crawler names. Public coverage badges and the integrations grid use accessible image labels; dashboard GEO, AI visibility, agent analytics, and social-listening surfaces now show provider marks where they identify measured sources. Text remains where it is necessary for filters or interpretation. Integration copy clarifies there is no implied endorsement.
- Added 18 Nuxtron-owned mini-workspace previews (nine for SEO and nine for Marketing) to the capability cards. They use shared palette tokens and are decorative to screen readers because each card already provides the capability name and explanation.
- Extended the shared SEO/Marketing product tour with visible-only auto-advance, a progress indicator, explicit play/pause, pause-on-focus/selection, and no automatic motion when reduced motion is preferred. Both product homepages use the same interaction.

### Verification

- TypeScript passed; the contrast audit found zero foreground/background pairs below 4.5:1.
- Full unit suite: 22 files and 182 tests passed. The provider registry’s 16 unit tests cover product labels, crawler aliases, unknown-label fallback, and local asset paths.
- Focused ESLint passed for the new modules, public sections, integrations, GEO, and social listening. Whole-file lint on the very large existing SEO-performance and Agent-Analytics modules still surfaces pre-existing rule/configuration findings away from the logo edits; this pass does not claim those files are lint-clean.
- Chrome responsive smoke run: 37 checks passed in the broad run. The initial run also exposed two issues: a first-load `/seo` dev-compilation timeout and an ambiguous tour-tablist selector. The route now has a scoped 90-second cold-start budget and passed at both widths; the corrected tour and public logo/preview checks passed 2/2. The separate muted, user-controlled film checks passed in the broad run.
