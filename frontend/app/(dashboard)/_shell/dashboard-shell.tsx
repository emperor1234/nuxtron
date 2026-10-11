"use client";

import {
  useEffect,
  useRef,
  useState,
  useSyncExternalStore,
  type ReactNode,
} from "react";
import Link from "next/link";
import Image from "next/image";
import { usePathname, useRouter } from "next/navigation";
import type { Route } from "next";
import * as Dialog from "@radix-ui/react-dialog";
import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import {
  Home,
  Search,
  ChartNoAxesCombined,
  MapPin,
  FileText,
  Share2,
  Clapperboard,
  LayoutGrid,
  Settings,
  Menu,
  X,
  ChevronDown,
  Plus,
  ScanEye,
  LogOut,
  ArrowLeftRight,
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
import { MENUS, RAIL_ITEMS, SETTINGS_ITEM, type RailKey } from "./nav";

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

const ICONS = {
  dashboard: Home,
  seo: Search,
  ai: ScanEye,
  traffic: ChartNoAxesCombined,
  local: MapPin,
  content: FileText,
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
    : { href: "/seo/domain-overview", label: "New analysis" };
}

function matchKey(path: string): RailKey {
  let best: RailKey = "dashboard";
  let length = -1;
  for (const item of ALL_RAILS)
    for (const prefix of [item.href, ...(item.matchPrefixes ?? [])]) {
      if (
        (path === prefix || path.startsWith(`${prefix}/`)) &&
        prefix.length > length
      ) {
        best = item.key;
        length = prefix.length;
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
  const router = useRouter();
  const activeKey = matchKey(pathname);
  const [expanded, setExpanded] = useState<RailKey | null>(null);
  const [mobile, setMobile] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const searchTrigger = useRef<HTMLButtonElement>(null);
  const session = useSyncExternalStore(
    subscribeSession,
    sessionSnapshot,
    serverSessionSnapshot,
  );
  const sessionUser = JSON.parse(session) as SessionUser | null;
  const product = useProductLine();
  const rails = visibleRailItems(ALL_RAILS, product);
  const action = primaryAction(product);
  const [workspace, setWorkspace] = useState("");
  useEffect(() => {
    const tenant = resolveSessionTenant();
    if (!tenant) return;
    let active = true;
    void apiGet("/white-label/profile", tenant)
      .then((profile) => {
        const whiteLabel = profile.white_label as
          | { profile?: { brand_name?: string } }
          | undefined;
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
  const closeSearch = () => setSearchOpen(false);

  function navigation(scope: string) {
    return (
      <>
        <div className={styles.brandRow}>
          <Link
            href="/dashboard"
            className={styles.logo}
            onClick={() => setMobile(false)}
          >
            <Image src="/brand/nuxtron-icon-square.svg" alt="" width={27} height={27} />
            Nuxtron
          </Link>
          {product && (
            <span className={styles.productBadge}>
              <span className="sr-only">Signed in to </span>
              {PRODUCT_META[product].label}
            </span>
          )}
        </div>
        <div className={styles.workspaceLabel}>
          <span className={styles.workspaceInitial} aria-hidden="true">
            {Array.from(workspace || "Workspace")[0]}
          </span>
          <div>
            <strong title={workspace || "Your workspace"}>
              {workspace || "Your workspace"}
            </strong>
            <small>{product ? PRODUCT_META[product].name : "All products"}</small>
          </div>
        </div>
        <p className={styles.navLabel}>Workspace</p>
        <nav className={styles.railNav} aria-label="Primary">
          {rails.map((item) => {
            const Icon = ICONS[item.key];
            const isExpanded = expanded === item.key;
            const section = MENUS[item.key];
            return (
              <div key={item.key}>
                {item.hasMenu ? (
                  <button
                    type="button"
                    className={`${styles.railItem} ${activeKey === item.key ? styles.railItemActive : ""}`}
                    aria-expanded={isExpanded}
                    aria-current={activeKey === item.key ? "location" : undefined}
                    aria-controls={`${scope}-nav-${item.key}`}
                    onClick={() => {
                      setExpanded(isExpanded ? null : item.key);
                      if (!isExpanded) router.push(item.href);
                    }}
                  >
                    <Icon size={18} aria-hidden="true" />
                    <span>{item.label}</span>
                    <ChevronDown
                      size={13}
                      className={styles.chevron}
                      aria-hidden="true"
                    />
                  </button>
                ) : (
                  <Link
                    href={item.href}
                    className={`${styles.railItem} ${activeKey === item.key ? styles.railItemActive : ""}`}
                    aria-current={pathname === item.href ? "page" : undefined}
                    onClick={() => {
                      setExpanded(null);
                      setMobile(false);
                    }}
                  >
                    <Icon size={18} aria-hidden="true" />
                    <span>{item.label}</span>
                  </Link>
                )}
                {isExpanded && section && (
                  <div
                    id={`${scope}-nav-${item.key}`}
                    className={styles.subnav}
                  >
                    {section.groups.map((group) => (
                      <div key={group.label}>
                        <p className={styles.flyoutGroupLabel}>{group.label}</p>
                        {group.items.map((entry) => (
                          <Link
                            key={entry.href}
                            href={entry.href}
                            className={styles.flyoutLink}
                            aria-current={
                              pathname === entry.href ? "page" : undefined
                            }
                            onClick={() => setMobile(false)}
                          >
                            {entry.label}
                          </Link>
                        ))}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </nav>
        <div className={styles.sidebarFoot}>
          <Link href="/account">
            Account settings <Settings size={14} aria-hidden="true" />
          </Link>
        </div>
      </>
    );
  }
  return (
    <div className={`nxScope ${styles.shell} ${fontClassName || ""}`}>
      <a href="#workspace-content" className="skip-to-content">
        Skip to workspace
      </a>
      <aside className={styles.rail}>{navigation("desktop")}</aside>
      <div className={styles.main}>
        <header className={styles.topbar}>
          <Dialog.Root open={mobile} onOpenChange={setMobile}>
            <Dialog.Trigger asChild>
              <button
                className={styles.mobileMenu}
                type="button"
                aria-label="Open workspace navigation"
              >
                <Menu size={20} />
              </button>
            </Dialog.Trigger>
            <Dialog.Portal>
              <Dialog.Overlay className={styles.mobileOverlay} />
              <Dialog.Content
                className={`nxScope ${styles.mobilePanel}`}
                aria-describedby={undefined}
              >
                <Dialog.Title className="sr-only">
                  Workspace navigation
                </Dialog.Title>
                <Dialog.Close
                  className={styles.mobileClose}
                  aria-label="Close workspace navigation"
                >
                  <X size={20} />
                </Dialog.Close>
                {navigation("mobile")}
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
            <span className={styles.searchText}>Search your workspace</span>
            <kbd className={styles.kbd}>⌘ K</kbd>
          </button>
          <div className={styles.topActions}>
            <Link
              href={action.href}
              className={styles.newReport}
              aria-label={action.label}
            >
              <Plus size={15} aria-hidden="true" />
              <span>{action.label}</span>
            </Link>
            <NotificationCenter />
            <AccountMenu
              email={sessionUser?.email}
              initials={sessionUser?.initials}
              product={product}
            />
          </div>
        </header>
        <CommandPalette
          open={searchOpen}
          onClose={closeSearch}
          returnFocusRef={searchTrigger}
        />
        <main id="workspace-content" tabIndex={-1} className={styles.content}>
          <DashboardRouteIdentity />
          {children}
        </main>
      </div>
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
        <button
          type="button"
          className={styles.userChip}
          aria-label="Account menu"
          title={email || "Account"}
        >
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
            <small>
              {product ? PRODUCT_META[product].name : "All Nuxtron products"}
            </small>
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
            onSelect={() =>
              leave(product ? PRODUCT_META[product].homePath : "/")
            }
          >
            <LogOut size={15} aria-hidden="true" />
            {leaving ? "Signing out…" : "Sign out"}
          </DropdownMenu.Item>
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  );
}
