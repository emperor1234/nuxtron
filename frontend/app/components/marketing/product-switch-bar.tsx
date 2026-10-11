"use client";

import Link from "next/link";
import type { Route } from "next";
import { usePathname } from "next/navigation";
import {
  PRODUCT_LINES,
  PRODUCT_META,
  type ProductLine,
} from "@/app/lib/product-line";

/**
 * Which product homepage the visitor is on. Only `/` and `/marketing*` belong
 * to a product; every other public page (pricing, blog, …) is neither, so the
 * switch shows no current segment there.
 */
export function currentProductHome(pathname: string): ProductLine | null {
  if (pathname === "/") return "seo";
  if (pathname === "/marketing" || pathname.startsWith("/marketing/")) return "marketing";
  return null;
}

type ProductSwitchProps = {
  /** "bar": slim ink strip above the desktop header. "drawer": full-width control in the mobile menu. */
  variant?: "bar" | "drawer";
  /** Called after a segment is chosen, e.g. to close the mobile drawer. */
  onNavigate?: () => void;
};

/**
 * Segmented control that moves between the two product homepages. Each
 * segment is a link, so it works without JavaScript and announces itself as
 * navigation; `aria-current` marks the product whose homepage is showing.
 */
export function ProductSwitch({ variant = "bar", onNavigate }: ProductSwitchProps) {
  const pathname = usePathname();
  const current = currentProductHome(pathname);
  const index = current ? PRODUCT_LINES.indexOf(current) : -1;

  return (
    <nav aria-label="Choose a product" className="mk-switch" data-variant={variant}>
      <div className="mk-switch-track">
        <span
          aria-hidden="true"
          className="mk-switch-indicator"
          data-visible={index >= 0 ? "true" : "false"}
          style={{ transform: `translateX(${Math.max(index, 0) * 100}%)` }}
        />
        {PRODUCT_LINES.map((product) => {
          const meta = PRODUCT_META[product];
          const isCurrent = product === current;
          return (
            <Link
              key={product}
              href={meta.homePath as Route}
              className="mk-switch-segment"
              aria-current={isCurrent ? "page" : undefined}
              onClick={onNavigate}
            >
              <span className="mk-switch-dot" aria-hidden="true" />
              {meta.name}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}

/** The slim bar above the main navigation (hidden below 960px, where the drawer carries the switch). */
export function ProductSwitchBar() {
  return (
    <div className="mk-switch-bar">
      <div className="mk-switch-bar-inner">
        <ProductSwitch variant="bar" />
        <p className="mk-switch-note">One account. Choose the product you sign in to.</p>
      </div>
    </div>
  );
}
