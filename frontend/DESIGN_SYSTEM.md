# Frontend UI ownership

Nuxtron has separate public-marketing and authenticated-product surfaces. Keep their component sources separate so visual and accessibility fixes remain centralized.

## Authenticated product (`app/(dashboard)`)

- Use `app/(dashboard)/_ui/kit.tsx` for page layout, headers, cards, buttons, fields, badges, tables, metrics, and data-status labels.
- Use semantic tokens from `app/(dashboard)/_ui/tokens.css`; do not introduce page-local brand colors when a token exists.
- Put page-specific composition in a colocated CSS module. Do not import public marketing components into product pages.
- Every data result must declare `DataStatus`: `live`, `preview`, or `unavailable`. Seeded, mock, demo, sample, and fallback responses are never `live`.
- Every data request needs loading, error, and honest empty states. The route-group boundaries are the baseline, not a replacement for request-level feedback.

## Public marketing (`app/(public)`)

- Use `components/ui`, `app/components/marketing`, and the public marketing styles.
- Marketing components must not become dependencies of dashboard product pages.

## Specialized effects

- `components/magicui` is optional presentation only. It must not own product semantics, forms, tables, navigation, loading, or error behavior.
- `app/components/shared` is for cross-route behavior that truly spans public and product surfaces. New visual primitives belong in the surface-specific system above.

## Review checklist

1. Is every primary feature reachable through the typed navigation or generated command palette?
2. Does each menu label lead to a distinct destination?
3. Does every data surface visibly identify live versus preview data?
4. Are loading, error, empty, keyboard-focus, and narrow-screen states defined?
5. Does the page use the owning surface's shared primitives and tokens?


## Brand marks, motion, and previews

- The Nuxtron-owned NX icon and wordmark are the only marks used as Nuxtron's brand. The shared accent is the original blue (`--brand: #2563c9`, with cyan `--brand-sky: #22cdea`); warm paper and ink remain the neutral foundation.
- Third-party provider assets live under `public/brand/providers/` and are rendered through surface-specific wrappers: `app/components/marketing/provider-logo.tsx` for public pages and `app/(dashboard)/_ui/provider-mark.tsx` for authenticated product pages. Keep provider artwork unchanged; use it only to identify coverage, integrations, or measured sources. Preserve accessible names and a text fallback; never imply endorsement or partnership.
- Capability-card miniatures are Nuxtron-owned illustrative UI shapes, not copied screenshots or claims about customer data. Their palette comes from shared tokens, and they remain decorative to assistive technology because the adjacent card already names the capability.
- The shared SEO/Marketing product tour is explanatory motion: it advances only while visible, pauses on tab interaction/focus, provides explicit play/pause controls, and does not auto-play for reduced-motion users.
