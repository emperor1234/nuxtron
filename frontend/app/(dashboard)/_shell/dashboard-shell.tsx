"use client";

import {
  useEffect,
  useMemo,
  useRef,
  useState,
  useSyncExternalStore,
  type ReactNode,
} from "react";
import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";
import type { Route } from "next";
import * as Dialog from "@radix-ui/react-dialog";
import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import {
  Home,
  Search,
  Share2,
  Clapperboard,
  LayoutGrid,
  Settings,
  Menu,
  X,
  ChevronDown,
  Plus,
  LogOut,
  ArrowLeftRight,
  type LucideIcon,
} from "lucide-react";
import { apiGet, resolveSessionTenant } from "@/app/lib/api-client";
import { readSessionUser, type SessionUser } from "@/app/lib/session-user";
import { otherProductLine, PRODUCT_META, type ProductLine } from "@/app/lib/product-line";
import {
  otherProductSignInHref,
  signOutAndNavigate,
  useProductLine,
  visibleRailItems,
} from "@/app/lib/use-product-line";
import NotificationCenter from "@/app/notification-center";
import styles from "./shell.module.css";
import "../_ui/tokens.css";
import CommandPalette from "./command-palette";
import DashboardRouteIdentity from "./route-identity";
import { MENUS, RAIL_ITEMS, SETTINGS_ITEM, type FlyoutMenu, type RailKey } from "./nav";

function subscribeSession(update: () => void) {
  window.addEventListener("storage", update);
  window.addEventListener("focus", update);
  return () => {
    window.removeEventListener("storage", update);
    window.removeEventListener("focus", update);
  };
}
function sessionSnapshot() {
  try {
    return JSON.stringify(readSessionUser());
  } catch {
    return "null";
  }
}
const serverSessionSnapshot = () => "null";

const ICONS: Record<RailKey, LucideIcon> = {
  dashboard: Home,
  seo: Search,
  social: Share2,
  studio: Clapperboard,
  apps: LayoutGrid,
  settings: Settings,
};
const ALL_RAILS = [...RAIL_ITEMS, SETTINGS_ITEM];

/** The topbar's primary action belongs to whichever product the user is in. */
function primaryAction(product: ProductLine | null): { href: Route; label: string } {
  return product === "marketing"
    ? { href: "/content-generation", label: "New content" }
    : { href: "/seo/on-page", label: "New analysis" };
}

function matchKey(path: string): RailKey {
  let best: RailKey = "dashboard";
  let length = -1;
  for (const item of ALL_RAILS) {
    const menuRoutes = MENUS[item.key]?.groups.flatMap((group) => group.items.map((entry) => entry.href)) ?? [];
    for (const prefix of [item.href, ...(item.matchPrefixes ?? []), ...menuRoutes]) {
      if ((path === prefix || path.startsWith(`${prefix}/`)) && prefix.length > length) {
        best = item.key;
        length = prefix.length;
      }
    }
  }
  return best;
}

/** The link that best matches the current path, so only one item looks active. */
function activeHref(menu: FlyoutMenu | undefined, path: string): string | null {
  let best: string | null = null;
  for (const group of menu?.groups ?? []) {
    for (const item of group.items) {
      if ((path === item.href || path.startsWith(`${item.href}/`)) && (best === null || item.href.length > best.length)) {
        best = item.href;
      }
    }
  }
  return best;
}

export default function DashboardShell({
  children,
  fontClassName,
}: {
  children: ReactNode;
  fontClassName?: string;
}) {
  const pathname = usePathname() || "/dashboard";
  const activeKey = matchKey(pathname);
  const [mobile, setMobile] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const searchTrigger = useRef<HTMLButtonElement>(null);
  const session = useSyncExternalStore(subscribeSession, sessionSnapshot, serverSessionSnapshot);
  const sessionUser = JSON.parse(session) as SessionUser | null;
  const product = useProductLine();
  const rails = visibleRailItems(ALL_RAILS, product).filter((item) => item.key !== "settings");
  const action = primaryAction(product);
  const [workspace, setWorkspace] = useState("");

  useEffect(() => {
    const tenant = resolveSessionTenant();
    if (!tenant) return;
    let active = true;
    void apiGet("/white-label/profile", tenant)
      .then((profile) => {
        const whiteLabel = profile.white_label as { profile?: { brand_name?: string } } | undefined;
        if (active) setWorkspace(whiteLabel?.profile?.brand_name?.trim() || "");
      })
      .catch(() => {
        /* Workspace naming is optional; keep the neutral label. */
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    const listener = (event: globalThis.KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setMobile(false);
        setSearchOpen(true);
      }
    };
    window.addEventListener("keydown", listener);
    return () => window.removeEventListener("keydown", listener);
  }, []);

  const menu = MENUS[activeKey];
  const hasPanel = Boolean(menu);

  function navigation(scope: string) {
    return (
      <>
        <nav className={styles.rail} aria-label="Products and sections">
          <Link href="/dashboard" className={styles.logo} onClick={() => setMobile(false)} aria-label="Nuxtron home">
            <Image src="/brand/nuxtron-icon-square.svg" alt="" width={32} height={32} />
          </Link>
          <ul className={styles.railList}>
            {rails.map((item) => {
              const Icon = ICONS[item.key];
              const current = activeKey === item.key;
              return (
                <li key={item.key}>
                  <Link
                    href={item.href}
                    className={`${styles.railItem} ${current ? styles.railItemActive : ""}`}
                    aria-current={pathname === item.href ? "page" : current ? "location" : undefined}
                    onClick={() => setMobile(false)}
                  >
                    <Icon size={20} aria-hidden="true" />
                    <span>{item.label}</span>
                  </Link>
                </li>
              );
            })}
          </ul>
          <Link
            href="/account"
            className={`${styles.railItem} ${activeKey === "settings" ? styles.railItemActive : ""}`}
            aria-current={pathname === "/account" ? "page" : activeKey === "settings" ? "location" : undefined}
            onClick={() => setMobile(false)}
          >
            <Settings size={20} aria-hidden="true" />
            <span>Account</span>
          </Link>
        </nav>
        {menu ? (
          <SectionPanel
            key={`${scope}-${activeKey}`}
            sectionKey={activeKey}
            menu={menu}
            pathname={pathname}
            workspace={workspace}
            product={product}
            onNavigate={() => setMobile(false)}
          />
        ) : null}
      </>
    );
  }

  return (
    <div className={`nxScope ${styles.shell} ${hasPanel ? "" : styles.shellNoPanel} ${fontClassName || ""}`}>
      <a href="#workspace-content" className="skip-to-content">
        Skip to workspace
      </a>
      <aside className={styles.sidebar}>{navigation("desktop")}</aside>
      <div className={styles.main}>
        <header className={styles.topbar}>
          <Dialog.Root open={mobile} onOpenChange={setMobile}>
            <Dialog.Trigger asChild>
              <button className={styles.mobileMenu} type="button" aria-label="Open workspace navigation">
                <Menu size={20} />
              </button>
            </Dialog.Trigger>
            <Dialog.Portal>
              <Dialog.Overlay className={styles.mobileOverlay} />
              <Dialog.Content className={`nxScope ${styles.mobilePanel}`} aria-describedby={undefined}>
                <Dialog.Title className="sr-only">Workspace navigation</Dialog.Title>
                <Dialog.Close className={styles.mobileClose} aria-label="Close workspace navigation">
                  <X size={20} />
                </Dialog.Close>
                <div className={styles.mobileBody}>{navigation("mobile")}</div>
              </Dialog.Content>
            </Dialog.Portal>
          </Dialog.Root>
          <button
            ref={searchTrigger}
            type="button"
            className={styles.search}
            onClick={() => setSearchOpen(true)}
            aria-label="Search tools and pages"
          >
            <Search size={16} aria-hidden="true" />
            <span className={styles.searchText}>Search tools and pages</span>
            <kbd className={styles.kbd}>⌘ K</kbd>
          </button>
          <div className={styles.topActions}>
            <Link href={action.href} className={styles.newReport} aria-label={action.label}>
              <Plus size={15} aria-hidden="true" />
              <span>{action.label}</span>
            </Link>
            <NotificationCenter />
            <AccountMenu email={sessionUser?.email} initials={sessionUser?.initials} product={product} />
          </div>
        </header>
        <CommandPalette open={searchOpen} onClose={() => setSearchOpen(false)} returnFocusRef={searchTrigger} />
        <main id="workspace-content" tabIndex={-1} className={styles.content}>
          <DashboardRouteIdentity />
          {children}
        </main>
      </div>
    </div>
  );
}

/** Contextual navigation for the active section, with a filter for long menus. */
function SectionPanel({
  sectionKey,
  menu,
  pathname,
  workspace,
  product,
  onNavigate,
}: {
  sectionKey: RailKey;
  menu: FlyoutMenu;
  pathname: string;
  workspace: string;
  product: ProductLine | null;
  onNavigate: () => void;
}) {
  const current = activeHref(menu, pathname);
  const initial = useMemo(() => {
    const open = new Set<string>();
    const owner = menu.groups.find((group) => group.items.some((item) => item.href === current));
    open.add(owner?.label ?? menu.groups[0]?.label ?? "");
    return open;
  }, [menu, current]);
  const [open, setOpen] = useState<Set<string>>(initial);
  const [query, setQuery] = useState("");
  const needle = query.trim().toLowerCase();
  const searching = needle.length > 0;
  const long = menu.groups.reduce((sum, group) => sum + group.items.length, 0) > 14;

  const groups = menu.groups
    .map((group) => ({
      ...group,
      items: searching
        ? group.items.filter((item) => `${item.label} ${item.description ?? ""}`.toLowerCase().includes(needle))
        : group.items,
    }))
    .filter((group) => group.items.length > 0);

  return (
    <div className={styles.panel}>
      <div className={styles.panelHead}>
        <Link href={(ALL_RAILS.find((item) => item.key === sectionKey)?.href ?? "/dashboard") as Route} className={styles.panelTitle} onClick={onNavigate}>
          {menu.title}
        </Link>
        <p className={styles.panelWorkspace} title={workspace || undefined}>
          {workspace || (product ? PRODUCT_META[product].name : "Your workspace")}
        </p>
      </div>
      {long ? (
        <div className={styles.panelFilter}>
          <Search size={14} aria-hidden="true" />
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder={`Filter ${menu.title} tools`}
            aria-label={`Filter ${menu.title} tools`}
          />
        </div>
      ) : null}
      <nav className={styles.panelNav} aria-label={`${menu.title} navigation`}>
        {groups.length === 0 ? <p className={styles.panelEmpty}>No tools match “{query}”.</p> : null}
        {groups.map((group) => {
          const expanded = searching || open.has(group.label);
          return (
            <div key={group.label} className={styles.panelGroup}>
              <button
                type="button"
                className={styles.groupToggle}
                aria-expanded={expanded}
                disabled={searching}
                onClick={() =>
                  setOpen((prev) => {
                    const next = new Set(prev);
                    if (next.has(group.label)) next.delete(group.label);
                    else next.add(group.label);
                    return next;
                  })
                }
              >
                <span>{group.label}</span>
                <ChevronDown size={14} className={expanded ? styles.chevronOpen : styles.chevron} aria-hidden="true" />
              </button>
              {expanded ? (
                <ul className={styles.groupList}>
                  {group.items.map((item) => (
                    <li key={item.href}>
                      <Link
                        href={item.href}
                        className={`${styles.panelLink} ${current === item.href ? styles.panelLinkActive : ""}`}
                        aria-current={pathname === item.href ? "page" : undefined}
                        onClick={onNavigate}
                      >
                        {item.label}
                      </Link>
                    </li>
                  ))}
                </ul>
              ) : null}
            </div>
          );
        })}
      </nav>
    </div>
  );
}

/**
 * Account menu. Moving to the other product signs the user out and opens that
 * product's sign-in: access is fixed at sign-in, so there is deliberately no
 * in-session switch.
 */
function AccountMenu({
  email,
  initials,
  product,
}: {
  email?: string;
  initials?: string;
  product: ProductLine | null;
}) {
  const [leaving, setLeaving] = useState(false);
  const switchTo = product
    ? {
        name: PRODUCT_META[otherProductLine(product)].name,
        from: PRODUCT_META[product].label,
        href: otherProductSignInHref(product),
      }
    : null;
  const leave = (href: string) => {
    if (leaving) return;
    setLeaving(true);
    void signOutAndNavigate(href);
  };
  return (
    <DropdownMenu.Root>
      <DropdownMenu.Trigger asChild>
        <button type="button" className={styles.userChip} aria-label="Account menu" title={email || "Account"}>
          <span className={styles.userAvatar} aria-hidden="true">
            {initials || "N"}
          </span>
        </button>
      </DropdownMenu.Trigger>
      <DropdownMenu.Portal>
        <DropdownMenu.Content
          align="end"
          sideOffset={8}
          collisionPadding={16}
          className={`nxScope ${styles.accountMenu}`}
        >
          <div className={styles.accountMenuHead}>
            <strong>{email || "Signed in"}</strong>
            <small>{product ? PRODUCT_META[product].name : "All Nuxtron products"}</small>
          </div>
          <DropdownMenu.Separator className={styles.accountMenuSeparator} />
          <DropdownMenu.Item asChild className={styles.accountMenuItem}>
            <Link href="/account">
              <Settings size={15} aria-hidden="true" />
              Account settings
            </Link>
          </DropdownMenu.Item>
          {switchTo && (
            <DropdownMenu.Item
              className={styles.accountMenuItem}
              disabled={leaving}
              onSelect={() => leave(switchTo.href)}
            >
              <ArrowLeftRight size={15} aria-hidden="true" />
              <span className={styles.accountMenuText}>
                Use {switchTo.name}
                <small>Signs you out of {switchTo.from}</small>
              </span>
            </DropdownMenu.Item>
          )}
          <DropdownMenu.Separator className={styles.accountMenuSeparator} />
          <DropdownMenu.Item
            className={styles.accountMenuItem}
            disabled={leaving}
            onSelect={() => leave(product ? PRODUCT_META[product].homePath : "/")}
          >
            <LogOut size={15} aria-hidden="true" />
            {leaving ? "Signing out…" : "Sign out"}
          </DropdownMenu.Item>
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  );
}
