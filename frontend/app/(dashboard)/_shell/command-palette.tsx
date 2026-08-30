'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import type { Route } from 'next';
import { ROUTE_INDEX } from './route-index.generated';
import styles from './shell.module.css';

type PaletteItem = {
  section: string;
  group: string;
  label: string;
  href: string;
  haystack: string;
};

const SECTION_LABELS: Record<string, string> = {
  dashboard: 'Home',
  seo: 'SEO',
  ai: 'AI',
  traffic: 'Traffic',
  local: 'Local',
  content: 'Content',
  social: 'Social',
  studio: 'Studio',
  apps: 'Apps',
  settings: 'Settings',
};

/**
 * Every route on disk, not just the ones someone remembered to add to the nav
 * model. The generated index is the reason this is ~240 entries rather than 57.
 */
const ITEMS: readonly PaletteItem[] = ROUTE_INDEX.filter((entry) => !entry.internal).map((entry) => {
  const section = SECTION_LABELS[entry.section] ?? entry.section;
  return {
    section,
    group: entry.group,
    label: entry.title,
    href: entry.route,
    haystack: [entry.title, entry.group, section, entry.route, ...entry.keywords].join(' ').toLowerCase(),
  };
});

const RECENTS_KEY = 'nuxtron.nav.recents';
const RECENTS_LIMIT = 6;

function readRecents(): PaletteItem[] {
  if (typeof window === 'undefined') return [];
  try {
    const raw = window.localStorage.getItem(RECENTS_KEY);
    if (!raw) return [];
    const hrefs: unknown = JSON.parse(raw);
    if (!Array.isArray(hrefs)) return [];
    return hrefs
      .map((href) => ITEMS.find((item) => item.href === href))
      .filter((item): item is PaletteItem => Boolean(item));
  } catch {
    return [];
  }
}

function pushRecent(href: string) {
  if (typeof window === 'undefined') return;
  try {
    const existing = readRecents().map((item) => item.href);
    const next = [href, ...existing.filter((entry) => entry !== href)].slice(0, RECENTS_LIMIT);
    window.localStorage.setItem(RECENTS_KEY, JSON.stringify(next));
  } catch {
    // A full or blocked localStorage must never stop navigation.
  }
}

/**
 * Lower is better. Ranking matters far more at 240 entries than at 57: a bare
 * `includes` filter buried "Keyword Research" under every route whose path
 * merely contains "keyword".
 */
function score(item: PaletteItem, query: string): number {
  const label = item.label.toLowerCase();
  if (label === query) return 0;
  if (label.startsWith(query)) return 1;
  if (label.includes(query)) return 2;
  // Word-boundary hit inside the label, e.g. "audit" -> "Site Audit".
  if (new RegExp(`\\b${query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}`).test(label)) return 3;
  if (item.haystack.includes(query)) return 4;
  return Number.POSITIVE_INFINITY;
}

export default function CommandPalette({ open, onClose }: { open: boolean; onClose: () => void }) {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLUListElement>(null);
  const [query, setQuery] = useState('');
  const [activeIndex, setActiveIndex] = useState(0);
  const [recents, setRecents] = useState<PaletteItem[]>([]);

  const results = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return recents.length ? recents : ITEMS.slice(0, 8);
    return ITEMS.map((item) => ({ item, rank: score(item, q) }))
      .filter((entry) => entry.rank !== Number.POSITIVE_INFINITY)
      .sort((a, b) => a.rank - b.rank || a.item.label.length - b.item.label.length)
      .slice(0, 20)
      .map((entry) => entry.item);
  }, [query, recents]);

  useEffect(() => {
    if (!open) return;
    setQuery('');
    setActiveIndex(0);
    setRecents(readRecents());
    const id = window.setTimeout(() => inputRef.current?.focus(), 20);
    return () => window.clearTimeout(id);
  }, [open]);

  useEffect(() => {
    setActiveIndex(0);
  }, [query]);

  // Keep the highlighted row visible when arrowing past the fold.
  useEffect(() => {
    listRef.current?.children[activeIndex]?.scrollIntoView({ block: 'nearest' });
  }, [activeIndex]);

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        onClose();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  const go = useCallback(
    (href: string) => {
      pushRecent(href);
      onClose();
      router.push(href as Route);
    },
    [onClose, router]
  );

  if (!open) return null;

  const showingRecents = !query.trim() && recents.length > 0;

  return (
    <div className={styles.paletteRoot}>
      <button type="button" className={styles.paletteBackdrop} aria-label="Close search" onClick={onClose} />
      <div className={styles.palettePanel} role="dialog" aria-modal="true" aria-label="Search tools">
        <input
          ref={inputRef}
          className={styles.paletteInput}
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder={`Search ${ITEMS.length} tools, reports and settings…`}
          aria-label="Search tools"
          role="combobox"
          aria-expanded
          aria-controls="nx-palette-list"
          aria-activedescendant={results[activeIndex] ? `nx-palette-option-${activeIndex}` : undefined}
          onKeyDown={(event) => {
            if (event.key === 'ArrowDown') {
              event.preventDefault();
              setActiveIndex((index) => (results.length ? (index + 1) % results.length : 0));
            }
            if (event.key === 'ArrowUp') {
              event.preventDefault();
              setActiveIndex((index) => (results.length ? (index - 1 + results.length) % results.length : 0));
            }
            if (event.key === 'Home') {
              event.preventDefault();
              setActiveIndex(0);
            }
            if (event.key === 'End') {
              event.preventDefault();
              setActiveIndex(Math.max(results.length - 1, 0));
            }
            if (event.key === 'Enter' && results[activeIndex]) {
              event.preventDefault();
              go(results[activeIndex].href);
            }
          }}
        />
        {showingRecents ? <p className={styles.paletteHint}>Recent</p> : null}
        <ul className={styles.paletteList} id="nx-palette-list" ref={listRef} role="listbox" aria-label="Results">
          {results.length === 0 ? (
            <li className={styles.paletteEmpty}>No tool matches “{query.trim()}”</li>
          ) : (
            results.map((item, index) => (
              <li key={item.href}>
                <button
                  type="button"
                  id={`nx-palette-option-${index}`}
                  role="option"
                  aria-selected={index === activeIndex}
                  className={`${styles.paletteItem} ${index === activeIndex ? styles.paletteItemActive : ''}`}
                  onMouseEnter={() => setActiveIndex(index)}
                  onClick={() => go(item.href)}
                >
                  <span className={styles.paletteItemLabel}>{item.label}</span>
                  <span className={styles.paletteItemMeta}>
                    {item.section} / {item.group}
                  </span>
                </button>
              </li>
            ))
          )}
        </ul>
      </div>
    </div>
  );
}
