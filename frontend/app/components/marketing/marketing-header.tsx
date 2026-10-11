"use client";

import { useState } from "react";
import Image from "next/image";
import Link from "next/link";
import type { Route } from "next";
import { usePathname } from "next/navigation";
import * as Dialog from "@radix-ui/react-dialog";
import { ArrowRight, ChevronDown, Menu, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { DEFAULT_PRODUCT_LINE, productAuthHref } from "@/app/lib/product-line";
import { MegaMenu } from "./mega-menu";
import { ProductSwitch, ProductSwitchBar, currentProductHome } from "./product-switch-bar";
import {
  MENU_LABELS,
  MOBILE_MENU_GROUPS,
  PRICING_LINK,
  type FeaturedPost,
  type MenuKey,
} from "./site-links";

const MENU_ORDER: readonly MenuKey[] = ["platform", "solutions", "tools", "resources", "company"];

/**
 * Public site chrome: the product switch bar, then the main navigation.
 * Sign-in links carry the product of the homepage the visitor is on, so the
 * account they create or open lands in the right dashboard.
 */
export function MarketingHeader({ featuredPost }: { featuredPost: FeaturedPost | null }) {
  const pathname = usePathname();
  const product = currentProductHome(pathname) ?? DEFAULT_PRODUCT_LINE;
  const loginHref = productAuthHref("/login", product);
  const startHref = productAuthHref("/register", product);

  return (
    <div className="mk-chrome">
      <ProductSwitchBar />
      <header className="mk-header">
        <div className="mk-header-inner">
          <Link href="/" className="mk-logo" aria-label="Nuxtron home">
            <Image src="/brand/nuxtron-icon-square.svg" alt="" width={29} height={29} className="mk-logo-mark" priority />
            Nuxtron
          </Link>
          <div className="mk-desktop-nav">
            <MegaMenu featuredPost={featuredPost} />
          </div>
          <div className="mk-header-actions">
            <Link href={loginHref as Route} className="mk-login-link">
              Log in
            </Link>
            <Button asChild size="sm">
              <Link href={startHref as Route}>
                Start free <ArrowRight data-icon="inline-end" />
              </Link>
            </Button>
            <MobileDrawer loginHref={loginHref} startHref={startHref} />
          </div>
        </div>
      </header>
    </div>
  );
}

function MobileDrawer({ loginHref, startHref }: { loginHref: string; startHref: string }) {
  const [open, setOpen] = useState(false);
  const close = () => setOpen(false);

  return (
    <Dialog.Root open={open} onOpenChange={setOpen}>
      <Dialog.Trigger className="mk-menu-button" aria-label="Open navigation">
        <Menu size={20} aria-hidden="true" />
      </Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className="mk-drawer-overlay" />
        <Dialog.Content className="mk-drawer" aria-describedby={undefined}>
          <div className="mk-drawer-head">
            <Dialog.Title className="mk-drawer-title">Menu</Dialog.Title>
            <Dialog.Close className="mk-menu-button mk-drawer-close" aria-label="Close navigation">
              <X size={20} aria-hidden="true" />
            </Dialog.Close>
          </div>

          <ProductSwitch variant="drawer" onNavigate={close} />

          <nav aria-label="Mobile" className="mk-drawer-nav">
            {MENU_ORDER.map((key) => (
              <details key={key} className="mk-drawer-group">
                <summary className="mk-drawer-summary">
                  {MENU_LABELS[key]}
                  <ChevronDown size={16} aria-hidden="true" className="mk-drawer-chevron" />
                </summary>
                {MOBILE_MENU_GROUPS[key].map((group) => (
                  <div key={group.id} className="mk-drawer-section">
                    <p className="mk-drawer-section-title">{group.title}</p>
                    <ul className="mk-drawer-links">
                      {group.links.map((link) => (
                        <li key={`${group.id}:${link.href}:${link.label}`}>
                          <Link href={link.href as Route} onClick={close}>
                            {link.label}
                          </Link>
                        </li>
                      ))}
                    </ul>
                  </div>
                ))}
              </details>
            ))}
            <Link href={PRICING_LINK.href as Route} className="mk-drawer-plain" onClick={close}>
              {PRICING_LINK.label}
            </Link>
          </nav>

          <div className="mk-drawer-actions">
            <Button asChild>
              <Link href={startHref as Route} onClick={close}>
                Start free <ArrowRight data-icon="inline-end" />
              </Link>
            </Button>
            <Link href={loginHref as Route} className="mk-drawer-login" onClick={close}>
              Log in
            </Link>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
