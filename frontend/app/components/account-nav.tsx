"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const ACCOUNT_LINKS = [
  { href: '/account', label: 'Overview' },
  { href: '/account/profile', label: 'Personal Details' },
  { href: '/account/orders', label: 'Orders' },
  { href: '/billing', label: 'Billing & Credits' },
];

export default function AccountNav() {
  const pathname = usePathname();

  return (
    <aside className="account-nav">
      <h3>Account</h3>
      <nav aria-label="Account sections">
        {ACCOUNT_LINKS.map((link) => {
          const current = pathname === link.href || (link.href === "/billing" && pathname.startsWith("/billing/"));
          return (
            <Link key={link.href} href={link.href} aria-current={current ? "page" : undefined}>
              {link.label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
