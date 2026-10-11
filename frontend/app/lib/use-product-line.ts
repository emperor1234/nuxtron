"use client";

import { useSyncExternalStore } from "react";
import {
  clearAuthSession,
  clearServerSession,
  STORAGE_SUPER_ADMIN_KEY,
} from "@/app/lib/api-client";
import {
  isRailVisible,
  otherProductLine,
  parseProductLine,
  productAuthHref,
  productForPath,
  PRODUCT_STORAGE_KEY,
  type ProductLine,
} from "@/app/lib/product-line";

/**
 * Client-side view of the product line the current session is restricted to.
 *
 * The httpOnly cookie read by proxy.ts is the authority; this hook reads the
 * localStorage mirror so the shell can hide the other product's navigation
 * without a round trip. `null` means unrestricted (admins, or sessions created
 * before product lines existed), and is also the server snapshot, so the first
 * render never depends on browser storage.
 */

function readStoredProduct(): ProductLine | null {
  try {
    return parseProductLine(globalThis.localStorage?.getItem(PRODUCT_STORAGE_KEY));
  } catch {
    // Blocked storage (private mode, sandboxed iframe) means "no restriction
    // known on the client"; proxy.ts still enforces the split server-side.
    return null;
  }
}

function subscribe(onChange: () => void): () => void {
  const onStorage = (event: { key: string | null }) => {
    if (event.key === null || event.key === PRODUCT_STORAGE_KEY) onChange();
  };
  window.addEventListener("storage", onStorage);
  window.addEventListener("focus", onChange);
  return () => {
    window.removeEventListener("storage", onStorage);
    window.removeEventListener("focus", onChange);
  };
}

const serverSnapshot = (): ProductLine | null => null;

export function useProductLine(): ProductLine | null {
  return useSyncExternalStore(subscribe, readStoredProduct, serverSnapshot);
}

/** Rail sections a user signed in to `product` may see, in their original order. */
export function visibleRailItems<T extends { product: ProductLine | "shared" }>(
  items: readonly T[],
  product: ProductLine | null,
): T[] {
  return items.filter((item) => isRailVisible(item.product, product));
}

/** Whether a dashboard route is reachable for a user signed in to `product`. */
export function isRouteVisible(route: string, product: ProductLine | null): boolean {
  const path = route.split(/[?#]/, 1)[0] || "/";
  return isRailVisible(productForPath(path), product);
}

/**
 * Validates the `?unavailable=` value proxy.ts appends when it bounces a deep
 * link to the other product. Returns the product the blocked page belongs to,
 * or `null` when there is nothing honest to say: an unknown value, no known
 * restriction, or a value naming the product the user is already signed in to.
 */
export function unavailableProductFrom(
  value: unknown,
  current: ProductLine | null,
): ProductLine | null {
  const raw = Array.isArray(value) ? value[0] : value;
  const requested = parseProductLine(raw);
  if (!requested || !current || requested === current) return null;
  return requested;
}

/**
 * Ends the current session and sends the browser to `href`. Product access is
 * fixed at sign-in, so moving to the other product always means signing in
 * again rather than flipping a flag on the live session.
 */
export async function signOutAndNavigate(href: string): Promise<void> {
  clearAuthSession();
  try {
    globalThis.localStorage?.removeItem(PRODUCT_STORAGE_KEY);
    globalThis.sessionStorage?.removeItem(STORAGE_SUPER_ADMIN_KEY);
  } catch {
    // Storage may be blocked; the server-side cookie clear below still runs.
  }
  await clearServerSession();
  globalThis.location.assign(href);
}

/** Sign-in link for the product the user is not currently signed in to. */
export function otherProductSignInHref(product: ProductLine): string {
  return productAuthHref("/login", otherProductLine(product));
}
