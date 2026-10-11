/**
 * Product lines — Nuxtron ships as two products that share one account system.
 *
 * A visitor chooses a product on the public site (the switch bar links `/` for
 * SEO and `/marketing` for Marketing) and carries that choice into sign-in as
 * `?product=`. After sign-in the dashboard shows only that product's sections
 * plus the shared ones (Home, Operations, Settings), and `proxy.ts` enforces
 * the same split server-side so a deep link cannot render the other product's
 * pages.
 *
 * The choice is a sign-in mode, not a paid entitlement: it is stored in an
 * httpOnly cookie set by `/api/auth/session`. If the backend later issues a
 * `product` claim in the session JWT, `resolveProductLine` prefers it, so
 * entitlement-based access slots in without changing any caller.
 *
 * This module is deliberately free of React and browser-only imports so the
 * edge proxy can use it.
 */

import { MENUS, RAIL_ITEMS, SETTINGS_ITEM, type RailKey } from "@/app/(dashboard)/_shell/nav";

export type ProductLine = "seo" | "marketing";

export const PRODUCT_LINES: readonly ProductLine[] = ["seo", "marketing"];
export const DEFAULT_PRODUCT_LINE: ProductLine = "seo";

/** httpOnly cookie read by proxy.ts; set and cleared by /api/auth/session. */
export const PRODUCT_COOKIE_NAME = "nuxtron_product";
/** localStorage mirror so client components can render without a round trip. */
export const PRODUCT_STORAGE_KEY = "nuxtron_product";
/** Query parameter carried from the public site into /login and /register. */
export const PRODUCT_QUERY_PARAM = "product";
/** Set on the /dashboard redirect when a route belongs to the other product. */
export const UNAVAILABLE_QUERY_PARAM = "unavailable";

export type ProductMeta = {
  /** Short name used in the switch bar and the dashboard badge. */
  label: string;
  /** Full product name for headings and sign-in copy. */
  name: string;
  /** Public homepage for this product. */
  homePath: "/" | "/marketing";
  /** One line describing what the product is for. */
  tagline: string;
};

export const PRODUCT_META: Readonly<Record<ProductLine, ProductMeta>> = {
  seo: {
    label: "SEO",
    name: "Nuxtron SEO",
    homePath: "/",
    tagline: "Search and AI answer-engine visibility.",
  },
  marketing: {
    label: "Marketing",
    name: "Nuxtron Marketing",
    homePath: "/marketing",
    tagline: "Content, social and customer work in one place.",
  },
};

/** Narrows untrusted input (query string, cookie, JWT claim) to a product line. */
export function parseProductLine(value: unknown): ProductLine | null {
  if (typeof value !== "string") return null;
  const normalised = value.trim().toLowerCase();
  return (PRODUCT_LINES as readonly string[]).includes(normalised) ? (normalised as ProductLine) : null;
}

/** The product a public pathname belongs to; anything outside /marketing is SEO. */
export function productForPublicPath(pathname: string): ProductLine {
  return pathname === "/marketing" || pathname.startsWith("/marketing/") ? "marketing" : "seo";
}

/** `/login?product=seo` style link that preserves the visitor's product choice. */
export function productAuthHref(base: "/login" | "/register", product: ProductLine): string {
  return `${base}?${PRODUCT_QUERY_PARAM}=${product}`;
}

export function otherProductLine(product: ProductLine): ProductLine {
  return product === "seo" ? "marketing" : "seo";
}

/** Whether a dashboard section is visible to a user signed in to `product`. */
export function isRailVisible(railProduct: ProductLine | "shared", product: ProductLine | null): boolean {
  return product === null || railProduct === "shared" || railProduct === product;
}

// ---------------------------------------------------------------------------
// Route ownership, derived from the dashboard navigation model so there is a
// single source of truth. Precedence, most specific first:
//   1. exact href listed in a section's flyout menu
//   2. a section's declared matchPrefixes
//   3. a section's base href as a path prefix (longest wins)
// A route claimed by both products, or by none, is "shared" and never blocked:
// locking a user out of an unknown page is worse than showing it.
// ---------------------------------------------------------------------------

type Owner = ProductLine | "shared";

const RAILS = [...RAIL_ITEMS, SETTINGS_ITEM];
const RAIL_PRODUCT = new Map<RailKey, Owner>(RAILS.map((rail) => [rail.key, rail.product]));

function merge(current: Owner | undefined, next: Owner): Owner {
  if (current === undefined || current === next) return next;
  return "shared";
}

const EXACT_OWNER: ReadonlyMap<string, Owner> = (() => {
  const owners = new Map<string, Owner>();
  for (const [key, menu] of Object.entries(MENUS)) {
    const owner = RAIL_PRODUCT.get(key as RailKey);
    if (!menu || !owner) continue;
    for (const group of menu.groups) {
      for (const item of group.items) {
        owners.set(item.href, merge(owners.get(item.href), owner));
      }
    }
  }
  for (const rail of RAILS) owners.set(rail.href, merge(owners.get(rail.href), rail.product));
  return owners;
})();

const PREFIX_OWNERS: readonly { prefix: string; owner: Owner }[] = RAILS.flatMap((rail) => [
  ...(rail.matchPrefixes ?? []).map((prefix) => ({ prefix, owner: rail.product })),
  { prefix: rail.href, owner: rail.product },
])
  .filter(({ prefix }) => prefix !== "/")
  .sort((a, b) => b.prefix.length - a.prefix.length);

/** Which product a dashboard pathname belongs to. */
export function productForPath(pathname: string): Owner {
  const path = pathname.length > 1 ? pathname.replace(/\/+$/, "") : pathname;
  const exact = EXACT_OWNER.get(path);
  if (exact) return exact;
  for (const { prefix, owner } of PREFIX_OWNERS) {
    if (path === prefix || path.startsWith(`${prefix}/`)) return owner;
  }
  return "shared";
}

/**
 * The product a session is restricted to, or `null` for unrestricted access.
 *
 * Unrestricted cases: admins, and sessions created before product lines
 * existed (no cookie, no claim) — those users keep the access they had rather
 * than being locked out of half the product mid-session.
 */
export function resolveProductLine(input: {
  claim?: unknown;
  cookie?: unknown;
  isAdmin?: boolean;
}): ProductLine | null {
  if (input.isAdmin) return null;
  return parseProductLine(input.claim) ?? parseProductLine(input.cookie);
}
