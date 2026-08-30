"use client";

import { useEffect, useState, type ReactNode } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { apiGet, resolveSessionTenant } from "@/app/lib/api-client";
import { readSessionUser, type SessionUser } from "@/app/lib/session-user";
import styles from "./shell.module.css";
import "../_ui/tokens.css";
import CommandPalette from "./command-palette";
import DashboardRouteIdentity from "./route-identity";
import { MENUS, RAIL_ITEMS, SETTINGS_ITEM, type RailKey } from "./nav";

const RAIL_ICONS: Record<RailKey, ReactNode> = {
  dashboard: (
    <path
      d="M4 11l8-7 8 7M6 9.5V20h12V9.5"
      stroke="currentColor"
      strokeWidth="1.9"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  ),
  seo: (
    <>
      <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="1.9" />
      <path
        d="M16 16l4.5 4.5"
        stroke="currentColor"
        strokeWidth="1.9"
        strokeLinecap="round"
      />
    </>
  ),
  ai: (
    <>
      <path
        d="M12 3l1.8 4.7L18.5 9l-4.7 1.8L12 15.5 10.2 10.8 5.5 9l4.7-1.3L12 3z"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinejoin="round"
      />
      <path
        d="M19 14l.7 1.9L21.5 16.5l-1.8.6L19 19l-.7-1.9L16.5 16.5l1.8-.6L19 14z"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
    </>
  ),
  traffic: (
    <>
      <path
        d="M5 20V12M12 20V5M19 20v-6"
        stroke="currentColor"
        strokeWidth="1.9"
        strokeLinecap="round"
      />
      <path
        d="M3 20h18"
        stroke="currentColor"
        strokeWidth="1.9"
        strokeLinecap="round"
      />
    </>
  ),
  local: (
    <>
      <path
        d="M12 21s7-6.3 7-11a7 7 0 10-14 0c0 4.7 7 11 7 11z"
        stroke="currentColor"
        strokeWidth="1.9"
        strokeLinejoin="round"
      />
      <circle cx="12" cy="10" r="2.5" stroke="currentColor" strokeWidth="1.9" />
    </>
  ),
  content: (
    <>
      <rect
        x="4"
        y="3"
        width="16"
        height="18"
        rx="2.5"
        stroke="currentColor"
        strokeWidth="1.9"
      />
      <path
        d="M8 8h8M8 12h8M8 16h5"
        stroke="currentColor"
        strokeWidth="1.9"
        strokeLinecap="round"
      />
    </>
  ),
  social: (
    <>
      <circle cx="6" cy="12" r="2.6" stroke="currentColor" strokeWidth="1.9" />
      <circle cx="18" cy="6" r="2.6" stroke="currentColor" strokeWidth="1.9" />
      <circle cx="18" cy="18" r="2.6" stroke="currentColor" strokeWidth="1.9" />
      <path
        d="M8.3 10.8l7.4-3.6M8.3 13.2l7.4 3.6"
        stroke="currentColor"
        strokeWidth="1.9"
      />
    </>
  ),
  studio: (
    <>
      <rect
        x="3"
        y="4.5"
        width="18"
        height="12"
        rx="2.2"
        stroke="currentColor"
        strokeWidth="1.9"
      />
      <path
        d="M10 8.8l4.2 2.2-4.2 2.2V8.8z"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinejoin="round"
      />
      <path
        d="M8.5 20h7"
        stroke="currentColor"
        strokeWidth="1.9"
        strokeLinecap="round"
      />
    </>
  ),
  apps: (
    <>
      <rect
        x="3.5"
        y="3.5"
        width="7"
        height="7"
        rx="1.6"
        stroke="currentColor"
        strokeWidth="1.9"
      />
      <rect
        x="13.5"
        y="3.5"
        width="7"
        height="7"
        rx="1.6"
        stroke="currentColor"
        strokeWidth="1.9"
      />
      <rect
        x="3.5"
        y="13.5"
        width="7"
        height="7"
        rx="1.6"
        stroke="currentColor"
        strokeWidth="1.9"
      />
      <rect
        x="13.5"
        y="13.5"
        width="7"
        height="7"
        rx="1.6"
        stroke="currentColor"
        strokeWidth="1.9"
      />
    </>
  ),
  settings: (
    <>
      <circle cx="12" cy="12" r="3" stroke="currentColor" strokeWidth="1.9" />
      <path
        d="M12 2v3M12 19v3M4.2 4.2l2.1 2.1M17.7 17.7l2.1 2.1M2 12h3M19 12h3M4.2 19.8l2.1-2.1M17.7 6.3l2.1-2.1"
        stroke="currentColor"
        strokeWidth="1.9"
        strokeLinecap="round"
      />
    </>
  ),
};

function RailIcon({ k }: { k: RailKey }) {
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
    >
      {RAIL_ICONS[k]}
    </svg>
  );
}

function matchKey(pathname: string): RailKey {
  const all = [...RAIL_ITEMS, SETTINGS_ITEM];
  let best: RailKey = "dashboard";
  let bestLen = -1;
  for (const item of all) {
    if (
      (pathname === item.href || pathname.startsWith(`${item.href}/`)) &&
      item.href.length > bestLen
    ) {
      best = item.key;
      bestLen = item.href.length;
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
  const [menuIntent, setMenuIntent] = useState<RailKey | "closed" | null>(null);
  const [searchOpen, setSearchOpen] = useState(false);
  const [sessionUser] = useState<SessionUser | null>(() => readSessionUser());
  const [workspaceLabel, setWorkspaceLabel] = useState("");
  const [unreadCount, setUnreadCount] = useState(0);
  const openMenu =
    menuIntent === "closed"
      ? null
      : (menuIntent ?? (activeKey !== "dashboard" ? activeKey : null));

  useEffect(() => {
    if (!openMenu) return;
    const onKey = (e: globalThis.KeyboardEvent) => {
      if (e.key === "Escape") setMenuIntent("closed");
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [activeKey, openMenu]);

  useEffect(() => {
    const onKey = (e: globalThis.KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setSearchOpen(true);
        setMenuIntent("closed");
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [activeKey]);

  useEffect(() => {
    const tenantId = sessionUser?.tenantId || resolveSessionTenant();
    if (!tenantId) return;

    let active = true;
    async function loadChrome() {
      try {
        const [profile, unread] = await Promise.allSettled([
          apiGet("/white-label/profile", tenantId),
          apiGet("/notifications/unread-count", tenantId),
        ]);
        if (!active) return;
        if (profile.status === "fulfilled") {
          const whiteLabel = profile.value.white_label as
            | Record<string, unknown>
            | undefined;
          const wlProfile = whiteLabel?.profile as
            | Record<string, unknown>
            | undefined;
          const brand =
            typeof wlProfile?.brand_name === "string"
              ? wlProfile.brand_name.trim()
              : "";
          const stage =
            typeof wlProfile?.stage === "string" ? wlProfile.stage.trim() : "";
          setWorkspaceLabel(brand || stage);
        }
        if (unread.status === "fulfilled") {
          const count = unread.value.unreadCount ?? unread.value.unread_count;
          setUnreadCount(typeof count === "number" ? count : 0);
        }
      } catch {
        if (active) setUnreadCount(0);
      }
    }
    void loadChrome();
    return () => {
      active = false;
    };
  }, [sessionUser]);

  const activeMenu = openMenu ? MENUS[openMenu] : null;

  const renderRailButton = (
    item: (typeof RAIL_ITEMS)[number] | typeof SETTINGS_ITEM,
  ) => {
    const isActive = (openMenu ?? activeKey) === item.key;
    const className = `${styles.railItem} ${isActive ? styles.railItemActive : ""}`;

    if (!item.hasMenu) {
      return (
        <Link
          key={item.key}
          href={item.href}
          className={className}
          aria-current={isActive ? "page" : undefined}
          onClick={() => setMenuIntent(null)}
        >
          <RailIcon k={item.key} />
          <span>{item.label}</span>
        </Link>
      );
    }

    const expanded = openMenu === item.key;
    return (
      <button
        key={item.key}
        type="button"
        className={className}
        aria-haspopup="true"
        aria-expanded={expanded}
        onClick={() => {
          if (openMenu !== item.key) {
            setMenuIntent(item.key);
            router.push(item.href);
            return;
          }
          setMenuIntent(expanded ? "closed" : item.key);
        }}
      >
        <RailIcon k={item.key} />
        <span>{item.label}</span>
      </button>
    );
  };

  return (
    <div
      className={`nxScope ${styles.shell}${fontClassName ? ` ${fontClassName}` : ""}`}
    >
      {/* ICON RAIL */}
      <aside className={styles.rail} aria-label="Primary">
        <nav className={styles.railNav}>{RAIL_ITEMS.map(renderRailButton)}</nav>
        <div className={styles.railBottom}>
          {renderRailButton(SETTINGS_ITEM)}
        </div>
      </aside>

      {/* FLYOUT */}
      {activeMenu ? (
        <>
          <button
            type="button"
            className={styles.flyoutOverlay}
            aria-label="Close menu"
            onClick={() => setMenuIntent("closed")}
          />
          <div
            className={styles.flyout}
            role="menu"
            aria-label={activeMenu.title}
          >
            <div className={styles.flyoutTitle}>{activeMenu.title}</div>
            <Link
              href="/dashboard"
              className={`${styles.flyoutLink} ${styles.flyoutLinkPrimary}`}
              role="menuitem"
              onClick={() => setMenuIntent(null)}
            >
              Dashboard
            </Link>
            {activeMenu.groups.map((group) => (
              <div key={group.label}>
                <div className={styles.flyoutGroupLabel}>{group.label}</div>
                {group.items.map((entry) => (
                  <Link
                    key={`${group.label}-${entry.label}`}
                    href={entry.href}
                    className={`${styles.flyoutLink} ${
                      pathname === entry.href ||
                      pathname.startsWith(`${entry.href}/`)
                        ? styles.flyoutLinkActive
                        : ""
                    }`}
                    aria-current={
                      pathname === entry.href ||
                      pathname.startsWith(`${entry.href}/`)
                        ? "page"
                        : undefined
                    }
                    role="menuitem"
                    onClick={() => setMenuIntent(openMenu)}
                  >
                    {entry.label}
                  </Link>
                ))}
              </div>
            ))}
          </div>
        </>
      ) : null}

      {/* MAIN */}
      <div
        className={`${styles.main} ${activeMenu ? styles.mainWithFlyout : ""}`}
      >
        <header className={styles.topbar}>
          <button
            type="button"
            className={styles.search}
            onClick={() => setSearchOpen(true)}
            aria-label="Search domains, keywords, reports"
          >
            <svg
              width="17"
              height="17"
              viewBox="0 0 24 24"
              fill="none"
              aria-hidden="true"
            >
              <circle
                cx="11"
                cy="11"
                r="7"
                stroke="currentColor"
                strokeWidth="1.9"
              />
              <path
                d="M16 16l4.5 4.5"
                stroke="currentColor"
                strokeWidth="1.9"
                strokeLinecap="round"
              />
            </svg>
            <span className={styles.searchText}>
              Search domains, keywords, reports…
            </span>
            <span className={styles.kbd}>⌘K</span>
          </button>
          <CommandPalette
            open={searchOpen}
            onClose={() => setSearchOpen(false)}
          />
          <div className={styles.topActions}>
            {sessionUser?.tenantId ? (
              <span className={styles.tenantChip} title={sessionUser.tenantId}>
                {workspaceLabel || sessionUser.tenantId}
              </span>
            ) : null}
            <Link
              href="/seo"
              className={styles.newReport}
              onClick={() => setMenuIntent(null)}
            >
              <svg
                width="15"
                height="15"
                viewBox="0 0 24 24"
                fill="none"
                aria-hidden="true"
              >
                <path
                  d="M12 5v14M5 12h14"
                  stroke="#fff"
                  strokeWidth="2.2"
                  strokeLinecap="round"
                />
              </svg>
              New analysis
            </Link>
            <Link
              href="/account"
              className={styles.bell}
              onClick={() => setMenuIntent(null)}
              aria-label={
                unreadCount > 0
                  ? `${unreadCount} unread notifications`
                  : "Notifications"
              }
            >
              <svg
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="none"
                aria-hidden="true"
              >
                <path
                  d="M6 9a6 6 0 1112 0c0 5 2 6 2 6H4s2-1 2-6z"
                  stroke="#5b6478"
                  strokeWidth="1.9"
                  strokeLinejoin="round"
                />
                <path
                  d="M10 20a2 2 0 004 0"
                  stroke="#5b6478"
                  strokeWidth="1.9"
                />
              </svg>
              {unreadCount > 0 ? <span className={styles.bellDot} /> : null}
            </Link>
            <Link
              href="/account"
              className={styles.userChip}
              onClick={() => setMenuIntent(null)}
            >
              <span className={styles.userAvatar}>
                {sessionUser?.initials || "·"}
              </span>
              <span className={styles.userMeta}>
                <span className={styles.userName}>
                  {sessionUser?.name || sessionUser?.email || "Account"}
                </span>
                <br />
                <span className={styles.userRole}>
                  {sessionUser?.email && sessionUser.name
                    ? sessionUser.email
                    : workspaceLabel || "Signed in"}
                </span>
              </span>
            </Link>
          </div>
        </header>

        <main className={styles.content}>
          <DashboardRouteIdentity />
          {children}
        </main>
      </div>
    </div>
  );
}
