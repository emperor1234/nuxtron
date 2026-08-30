'use client';

import { useEffect, useState, type ReactNode } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import styles from './shell.module.css';
import '../_ui/tokens.css';
import CommandPalette from './command-palette';
import { MENUS, RAIL_ITEMS, SETTINGS_ITEM, type RailKey } from './nav';

const RAIL_ICONS: Record<RailKey, ReactNode> = {
  dashboard: (
    <path d="M4 11l8-7 8 7M6 9.5V20h12V9.5" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" />
  ),
  seo: (
    <>
      <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="1.9" />
      <path d="M16 16l4.5 4.5" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" />
    </>
  ),
  ai: (
    <>
      <path d="M12 3l1.8 4.7L18.5 9l-4.7 1.8L12 15.5 10.2 10.8 5.5 9l4.7-1.3L12 3z" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />
      <path d="M19 14l.7 1.9L21.5 16.5l-1.8.6L19 19l-.7-1.9L16.5 16.5l1.8-.6L19 14z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
    </>
  ),
  traffic: (
    <>
      <path d="M5 20V12M12 20V5M19 20v-6" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" />
      <path d="M3 20h18" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" />
    </>
  ),
  local: (
    <>
      <path d="M12 21s7-6.3 7-11a7 7 0 10-14 0c0 4.7 7 11 7 11z" stroke="currentColor" strokeWidth="1.9" strokeLinejoin="round" />
      <circle cx="12" cy="10" r="2.5" stroke="currentColor" strokeWidth="1.9" />
    </>
  ),
  content: (
    <>
      <rect x="4" y="3" width="16" height="18" rx="2.5" stroke="currentColor" strokeWidth="1.9" />
      <path d="M8 8h8M8 12h8M8 16h5" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" />
    </>
  ),
  social: (
    <>
      <circle cx="6" cy="12" r="2.6" stroke="currentColor" strokeWidth="1.9" />
      <circle cx="18" cy="6" r="2.6" stroke="currentColor" strokeWidth="1.9" />
      <circle cx="18" cy="18" r="2.6" stroke="currentColor" strokeWidth="1.9" />
      <path d="M8.3 10.8l7.4-3.6M8.3 13.2l7.4 3.6" stroke="currentColor" strokeWidth="1.9" />
    </>
  ),
  apps: (
    <>
      <rect x="3.5" y="3.5" width="7" height="7" rx="1.6" stroke="currentColor" strokeWidth="1.9" />
      <rect x="13.5" y="3.5" width="7" height="7" rx="1.6" stroke="currentColor" strokeWidth="1.9" />
      <rect x="3.5" y="13.5" width="7" height="7" rx="1.6" stroke="currentColor" strokeWidth="1.9" />
      <rect x="13.5" y="13.5" width="7" height="7" rx="1.6" stroke="currentColor" strokeWidth="1.9" />
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
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      {RAIL_ICONS[k]}
    </svg>
  );
}

function matchKey(pathname: string): RailKey {
  const all = [...RAIL_ITEMS, SETTINGS_ITEM];
  let best: RailKey = 'dashboard';
  let bestLen = -1;
  for (const item of all) {
    if ((pathname === item.href || pathname.startsWith(`${item.href}/`)) && item.href.length > bestLen) {
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
  const pathname = usePathname() || '/dashboard';
  const activeKey = matchKey(pathname);
  const [openMenu, setOpenMenu] = useState<RailKey | null>(null);
  const [searchOpen, setSearchOpen] = useState(false);

  // Close the flyout whenever navigation completes or Escape is pressed.
  useEffect(() => {
    setOpenMenu(null);
  }, [pathname]);

  useEffect(() => {
    if (!openMenu) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpenMenu(null);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [openMenu]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setSearchOpen(true);
        setOpenMenu(null);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  const activeMenu = openMenu ? MENUS[openMenu] : null;

  const renderRailButton = (item: (typeof RAIL_ITEMS)[number] | typeof SETTINGS_ITEM) => {
    const isActive = activeKey === item.key;
    const className = `${styles.railItem} ${isActive ? styles.railItemActive : ''}`;

    if (!item.hasMenu) {
      return (
        <Link key={item.key} href={item.href} className={className} aria-current={isActive ? 'page' : undefined}>
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
        onClick={() => setOpenMenu((cur) => (cur === item.key ? null : item.key))}
      >
        <RailIcon k={item.key} />
        <span>{item.label}</span>
      </button>
    );
  };

  return (
    <div className={`nxScope ${styles.shell}${fontClassName ? ` ${fontClassName}` : ''}`}>
      {/* ICON RAIL */}
      <aside className={styles.rail} aria-label="Primary">
        <Link href="/dashboard" className={styles.railLogo} aria-label="Nuxtron home">
          <svg width="19" height="19" viewBox="0 0 24 24" fill="none">
            <path d="M4 18V6l8 7 8-7v12" stroke="#fff" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </Link>
        <nav className={styles.railNav}>{RAIL_ITEMS.map(renderRailButton)}</nav>
        <div className={styles.railBottom}>
          {renderRailButton(SETTINGS_ITEM)}
          <Link href="/account" className={styles.railAvatar} aria-label="Your account">
            MA
          </Link>
        </div>
      </aside>

      {/* FLYOUT */}
      {activeMenu ? (
        <>
          <button type="button" className={styles.flyoutOverlay} aria-label="Close menu" onClick={() => setOpenMenu(null)} />
          <div className={styles.flyout} role="menu" aria-label={activeMenu.title}>
            <div className={styles.flyoutTitle}>{activeMenu.title}</div>
            <Link href="/dashboard" className={`${styles.flyoutLink} ${styles.flyoutLinkPrimary}`} role="menuitem">
              Dashboard
            </Link>
            {activeMenu.groups.map((group) => (
              <div key={group.label}>
                <div className={styles.flyoutGroupLabel}>{group.label}</div>
                {group.items.map((entry) => (
                  <Link key={`${group.label}-${entry.label}`} href={entry.href} className={styles.flyoutLink} role="menuitem">
                    {entry.label}
                  </Link>
                ))}
              </div>
            ))}
          </div>
        </>
      ) : null}

      {/* MAIN */}
      <div className={styles.main}>
        <header className={styles.topbar}>
          <button
            type="button"
            className={styles.search}
            onClick={() => setSearchOpen(true)}
            aria-label="Search domains, keywords, reports"
          >
            <svg width="17" height="17" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="1.9" />
              <path d="M16 16l4.5 4.5" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" />
            </svg>
            <span className={styles.searchText}>Search domains, keywords, reports…</span>
            <span className={styles.kbd}>⌘K</span>
          </button>
          <CommandPalette open={searchOpen} onClose={() => setSearchOpen(false)} />
          <div className={styles.topActions}>
            <button type="button" className={styles.datePill}>
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <rect x="3" y="4" width="18" height="17" rx="2" stroke="#5b6478" strokeWidth="1.9" />
                <path d="M3 9h18M8 2v4M16 2v4" stroke="#5b6478" strokeWidth="1.9" strokeLinecap="round" />
              </svg>
              <span>Last 30 days</span>
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <path d="M6 9l6 6 6-6" stroke="#9aa1b2" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </button>
            <button type="button" className={styles.newReport}>
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <path d="M12 5v14M5 12h14" stroke="#fff" strokeWidth="2.2" strokeLinecap="round" />
              </svg>
              New report
            </button>
            <button type="button" className={styles.bell} aria-label="Notifications">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <path d="M6 9a6 6 0 1112 0c0 5 2 6 2 6H4s2-1 2-6z" stroke="#5b6478" strokeWidth="1.9" strokeLinejoin="round" />
                <path d="M10 20a2 2 0 004 0" stroke="#5b6478" strokeWidth="1.9" />
              </svg>
              <span className={styles.bellDot} />
            </button>
            <Link href="/account" className={styles.userChip}>
              <span className={styles.userAvatar}>MA</span>
              <span className={styles.userMeta}>
                <span className={styles.userName}>Maya Adler</span>
                <br />
                <span className={styles.userRole}>Growth team</span>
              </span>
            </Link>
          </div>
        </header>

        <main className={styles.content}>{children}</main>
      </div>
    </div>
  );
}
