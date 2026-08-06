# Nuxtron Public Website Rebuild Specification

Status: implementation in progress — public foundation, homepage, product catalog/details, solution details, and trust center completed  
Scope: every public page; dashboard and authenticated product surfaces are excluded  
Design read: premium B2B AI growth platform with HubSpot-level clarity and conversion structure, Stripe-level product storytelling and motion, and a distinct Nuxtron identity.

## 1. What the current frontend contains

The public route group currently contains:

- Core marketing: `/`, `/features`, `/products`, `/solutions`, `/use-cases`, `/pricing`, `/tools`, `/about`, `/contact`
- Feature detail: `/features/ai-visibility-tracking`, `/features/brand-visibility`, `/features/citation-analytics`, `/features/content-optimization`, `/features/core-web-vitals-automator`, `/features/keyword-planner`
- Tool detail: `/tools/translation-studio`
- Acquisition/auth: `/subscribe`, `/login`, `/register`, `/reset-password`
- Legal: `/privacy`, `/terms`

The code already has a shared public layout, navigation, footer, design tokens, page sections, product mockups, scroll reveal, a logo marquee, and Framer Motion. Keep these foundations, but rebuild the visual system and page composition rather than layering another theme over the existing one.

### Problems to fix during the rebuild

- Public pages mix multiple visual generations: global purple dashboard styles, `cin-*` legacy tokens, and newer `nx-*` cream/orange tokens.
- The homepage repeats three alternating split sections, which makes the experience feel templated.
- Several visuals are emoji or CSS mockups. Replace these with real product captures, purpose-built illustrations, or generated campaign imagery.
- Marketing claims such as customer counts, keyword totals, ROAS lifts, and testimonials must not ship unless verified.
- The sitemap references `/platform`, `/cost-saving-calculator`, and `/ai-search-impact-calculator`, which currently live in the dashboard route group rather than the public site.
- The existing token comments describe copying reference-site computed styles. The rebuild should borrow principles, not proprietary brand expression or exact values.
- Public marketing should not inherit the dashboard body's grid, purple glows, heading scale, or `main` width constraints.

## 2. Recommended information architecture

### Primary navigation

Use five stable items on desktop so the navigation remains one line:

1. Platform — mega menu for platform overview and product pillars
2. Solutions — by team and business outcome
3. Resources — free tools, customer stories, guides, and help
4. Pricing
5. Company — about, contact, trust

Right side: `Log in`, `Book a demo`, and one primary CTA labeled `Start free`. Use those same labels everywhere; do not invent synonymous CTA labels page by page.

### Phase 1: pages required for launch

| Page | Route | Purpose | Signature interaction |
|---|---|---|---|
| Homepage | `/` | Explain the unified platform and route visitors by goal | Interactive workflow hero; product canvas responds to selected growth goal |
| Platform overview | `/platform` | Show how data, agents, and channels work together | Scroll-linked three-layer platform diagram |
| Products overview | `/products` | Browse the main product pillars | Hover/focus product map with changing product preview |
| SEO & AI visibility | `/products/seo-ai-visibility` | Consolidate SEO, AEO/GEO, tracking, and optimization | Search-to-answer animated journey with live tabs |
| Social media | `/products/social-media` | Publishing, inbox, listening, analytics | Clickable calendar/inbox prototype |
| Paid media | `/products/paid-media` | Campaign creation and optimization | Budget allocation simulation with reduced-motion fallback |
| Content studio | `/products/content-studio` | Creation, repurposing, brand voice | Source-to-multichannel transformation sequence |
| Reviews & reputation | `/products/reputation` | Review capture, response, and insights | Review stream and response-generation demo |
| Analytics & attribution | `/products/analytics` | Unified performance and revenue story | Metric lens changes the same dataset without page reload |
| AI agents | `/products/ai-agents` | Explain autonomous work and human controls | Agent run timeline with approval checkpoints |
| Solutions overview | `/solutions` | Route users to the right outcome/team page | Goal selector that updates relevant workflows |
| Agencies | `/solutions/agencies` | Multi-client, approvals, reporting, white label | Workspace switcher and approval flow |
| Enterprise | `/solutions/enterprise` | Governance, security, scale, procurement | Architecture/security control explorer |
| Small teams | `/solutions/small-business` | Fast setup and unified tool replacement | Before/after stack-cost comparison |
| Use cases | `/use-cases` | Outcome-led discovery | Filterable, URL-addressable use-case library |
| Pricing | `/pricing` | Help visitors choose and convert | Monthly/annual control, team-size estimator, comparison drawer |
| Free tools | `/tools` | Acquisition and product sampling | Search/filter directory with immediate tool previews |
| Translation Studio | `/tools/translation-studio` | Keep the existing working tool | Preserve workflow; reskin with the public system |
| About | `/about` | Mission, principles, company credibility | Lightweight milestone line; no decorative motion overload |
| Contact / demo | `/contact` | Qualify and route sales conversations | Progressive form with inline success/error states |
| Trust center | `/trust` | Security, privacy, compliance, reliability | Filterable control categories and document request flow |
| Login | `/login` | Product access | Focused auth shell; no marketing footer |
| Register | `/register` | Free account conversion | Short progressive signup with expectations shown upfront |
| Reset password | `/reset-password` | Account recovery | Clear success, error, resend, and expired-link states |
| Privacy | `/privacy` | Legal requirement | Sticky in-page contents on desktop |
| Terms | `/terms` | Legal requirement | Sticky in-page contents on desktop |

The six current `/features/*` routes should redirect into the appropriate product page anchors unless search demand justifies distinct pages. This prevents thin, repetitive feature pages. Keep a standalone detail route only when it can support unique proof, visuals, FAQs, and intent-specific copy.

### Phase 2: high-value growth pages

- `/customers` and `/customers/[slug]` — only after real, approved stories exist.
- `/integrations` and `/integrations/[slug]` — searchable integration catalog.
- `/resources` — guides, reports, webinars, and templates.
- `/blog` and `/blog/[slug]` — editorial acquisition layer.
- `/compare/[competitor]` — evidence-led comparison pages, never unsupported attack copy.
- `/solutions/ecommerce`, `/solutions/saas`, `/solutions/local-business` — add only from validated demand.
- `/status` and `/docs` — link to dedicated systems when they exist; do not fake them as marketing pages.

`/subscribe` should become an inline newsletter component and a compact confirmation route, not a primary standalone destination.

## 3. Visual direction

### Core principles

- Borrow HubSpot's plain-language hierarchy, generous proof, useful mega navigation, and obvious conversion paths.
- Borrow Stripe's asymmetric editorial grids, layered product visuals, technical confidence, sectional color shifts, and scroll-linked storytelling.
- Do not copy either site's colors, typography, illustrations, gradients, page order, wording, or animations.
- Nuxtron's own visual idea is an “orchestration field”: fine paths connect content, search, social, ads, reviews, and revenue into one living system.

### Design dials

- `DESIGN_VARIANCE: 7/10` — asymmetric but commercially legible.
- `MOTION_INTENSITY: 6/10` — interactive product storytelling, never spectacle for its own sake.
- `VISUAL_DENSITY: 4/10` — airy marketing pages with dense product moments where they prove capability.

### Palette

Move away from the current generic AI-purple globals and from HubSpot-like orange as the defining brand.

| Token | Value | Use |
|---|---:|---|
| Canvas | `#F7F8F4` | Primary warm-neutral background |
| Surface | `#FFFFFF` | Product frames and forms |
| Ink | `#101828` | Primary text and dark sections |
| Muted ink | `#52606D` | Body copy |
| Hairline | `#DDE2E7` | Borders and separators |
| Brand cobalt | `#3157F6` | Primary CTA, links, focus, selected states |
| Cobalt dark | `#1837B8` | Hover/pressed state |
| Cobalt tint | `#E9EEFF` | Soft branded surfaces |
| Positive | `#16794A` | Verified success states only |
| Warning | `#9A5B00` | Warnings only |

Use one accent—cobalt—through the core site. Product categories may use muted supporting tints in illustrations, but buttons and links remain cobalt. Gradients should be rare, broad, and low-saturation; never glowing purple blobs behind generic cards.

### Typography

Use `next/font` throughout.

- Display and body: **Manrope**, already installed and distinctive enough for Nuxtron. Use weights 400, 500, 600, 700, and 800.
- UI/data labels: **Inter**, already installed, at 400–600 for compact product mockups only.
- Code and technical values: system monospace or add **Geist Mono** only if genuine code samples become part of the marketing site.
- Retire Sora from the public marketing layer; it can remain in the dashboard until that system is separately revisited.
- Do not introduce a decorative serif. The product is technical B2B software, not editorial luxury.

Suggested scale:

- Hero display: `clamp(3.25rem, 7vw, 6.75rem)`, 0.94 line-height, `-0.055em` tracking; use only for short headlines.
- Page H1: `clamp(2.75rem, 5.5vw, 5.25rem)`.
- Section H2: `clamp(2rem, 4vw, 3.75rem)`.
- H3: `clamp(1.25rem, 2vw, 1.75rem)`.
- Body large: `1.125rem–1.25rem`, max 62 characters.
- Body: `1rem`, 1.65 line-height.
- UI labels: `0.8125rem–0.9375rem`; sentence case by default.

### Shape, spacing, and material

- Buttons: 10px radius; cards: 18px; product frames: 24px; fields: 10px. Pills are reserved for filters, status, and segmented controls.
- Container: 1280px maximum with `clamp(20px, 5vw, 72px)` horizontal gutters.
- Section spacing: 96–160px desktop, 64–96px mobile.
- Use borders and spacing before shadows. Product frames may use a tinted, layered shadow; generic feature cards should not.
- Alternate the canvas deliberately: warm neutral, white, dark ink, and very light cobalt sections. Each color change must signal a new chapter.
- Use real product interface captures or carefully composed product demos. Never show a UI that promises functionality the application does not have.

## 4. Homepage composition

Avoid rebuilding the current three-row SEO/social/ads zigzag. Recommended sequence:

1. **Hero:** left-aligned short outcome headline and two CTAs; right side is an interactive Nuxtron orchestration canvas. Keep all primary actions visible in the first viewport.
2. **Customer proof:** approved customer logos or, until available, verified operational facts. No invented logo wall.
3. **Platform story:** a full-width connected-system diagram where selecting Data, Agents, or Channels changes the explanation and visual.
4. **Outcome switcher:** tabs for “Be found,” “Create,” “Distribute,” and “Convert,” each updating one shared product stage.
5. **Flagship workflow:** scroll-linked but user-controllable sequence: insight → plan → approval → execution → revenue signal.
6. **Product constellation:** asymmetric product grid with three visually rich cells and three concise utility rows—not six identical cards.
7. **Measured proof:** one real customer story or case-study module; if none exists, show no testimonial.
8. **Enterprise trust:** security architecture, human approval, permissions, and integrations.
9. **Pricing bridge:** concise plan positioning with a direct link to the full comparison.
10. **Closing CTA:** one direct conversion message using `Start free` and `Book a demo`.

Use no more than three eyebrow labels across the ten sections. Each section should have a distinct layout family.

## 5. Interaction and motion language

### Global interactions

- Sticky header begins transparent/flat, becomes a solid surface after 12–24px scroll.
- Mega menu opens on click and intentional hover, supports keyboard arrows/Escape, and does not vanish across a pointer gap.
- Links use a directional arrow that moves 3–4px on hover; buttons translate by 1px or scale to 0.98 on press.
- Cards reveal additional information through real state changes, not decorative tilting.
- Section entrances use opacity plus 16–24px translation over 450–650ms. Stagger only tightly related items.
- Product animations pause when off-screen and never update React state on every pointer or scroll event; use Motion values/transforms.

### Signature interactions

- **Orchestration canvas:** pointer proximity highlights connected nodes on desktop; tap selects a node on mobile.
- **Sticky product chapter:** text steps advance the product visual, but users can also click tabs and scroll normally.
- **Metric lens:** one segmented control changes which metrics are emphasized within a consistent chart.
- **Pricing estimator:** team size and required workflows produce a clear recommended plan without hiding the full price table.
- **Tool directory:** searchable/filterable with query parameters so filtered views can be linked.

### Accessibility and performance rules

- Every animation must have a meaningful static `prefers-reduced-motion` state.
- Never rely on hover; every reveal must also work by focus and tap.
- Maintain WCAG AA contrast, visible cobalt focus rings, semantic headings, landmark regions, and a skip link.
- Respect touch targets of at least 44×44px.
- Keep first-load interactive JavaScript lean. Static page structure should be server-rendered; motion and calculators should be isolated client leaves.
- Reserve media dimensions to prevent layout shift. Prefer AVIF/WebP and responsive `next/image`.
- Target LCP under 2.5s, INP under 200ms, CLS under 0.1 on a mid-range mobile connection.

## 6. Reusable component system

Build these once and use them across the public site:

- `MarketingShell`, `MarketingHeader`, `MegaMenu`, `MobileMenu`, `MarketingFooter`
- `HeroSplit`, `HeroProductStage`, `PageIntro`
- `LogoWall`, `ProofBar`, `MetricStory`, `CustomerStory`
- `ProductStage`, `ProductTabs`, `WorkflowStepper`, `ArchitectureMap`
- `FeatureRows`, `OutcomeSwitcher`, `ProductConstellation`
- `PricingEstimator`, `PlanTable`, `ComparisonDrawer`, `FaqAccordion`
- `ResourceCard`, `ToolCard`, `FilterBar`, `SearchField`
- `LeadForm`, `NewsletterForm`, `AuthShell`
- `FinalCta`, `LegalLayout`, `InPageNav`

Static sections should be Server Components. Only menus, tabs, forms, calculators, and animated product stages should use `'use client'`.

## 7. Content rules

- Lead with outcomes, then show the system that produces them.
- A hero subhead is at most 20 words; a hero has at most one eyebrow, one headline, one subhead, and one CTA group.
- Use one label per CTA intent: `Start free`, `Book a demo`, `View pricing`, `Explore [product]`.
- Replace vague AI language such as “revolutionize” and “unlock” with concrete verbs: find, plan, create, approve, publish, measure.
- Every product page must include: target user, problem, workflow, key capabilities, product proof, integrations, security/control context, related products, FAQ, and conversion CTA.
- Any statistic, customer quote, compliance statement, or logo needs a source and approval field in the content model.
- Do not describe the system as autonomous without showing where users review, approve, pause, and audit work.

## 8. Migration plan

### Phase A — foundation

1. Separate marketing base styles from dashboard globals under `.nx-public-root` or a dedicated marketing stylesheet.
2. Replace the existing `nx-*`/`cin-*` compatibility stack with one documented token layer.
3. Rebuild the header, footer, buttons, typography, form fields, and accessibility primitives.
4. Create a content/data layer for navigation, products, solutions, pricing, proof, and FAQs.

### Phase B — conversion core

1. Rebuild homepage.
2. Build platform and product overview.
3. Build pricing and contact/demo flow.
4. Rebuild auth pages in the same family without adding marketing distractions.

### Phase C — product and solution depth

1. Build the seven product pages from shared templates with unique interactions.
2. Build agencies, enterprise, and small-business solution pages.
3. Consolidate/redirect thin feature pages.

### Phase D — acquisition and trust

1. Rebuild tools and Translation Studio.
2. Add trust center, resources, and real customer stories.
3. Correct sitemap, metadata, structured data, canonical links, and redirects.

### Phase E — quality gate

- Test at 360, 390, 768, 1024, 1280, and 1536px.
- Run keyboard, screen-reader landmarks, reduced-motion, contrast, and zoom checks.
- Add Playwright coverage for menus, CTA routing, pricing controls, forms, auth states, and all public routes.
- Capture Lighthouse/Core Web Vitals baselines before and after the rebuild.
- Require content approval for every public claim before launch.

## 9. Definition of done

The rebuild is complete when all public routes use one visual system; every navigation item resolves; there are no dashboard-style leaks; mobile interactions are explicit; all forms include loading, success, empty, and error states; motion respects user preferences; proof is verified; SEO routes and sitemap are correct; and the site feels like Nuxtron—not a skin of HubSpot or Stripe.
