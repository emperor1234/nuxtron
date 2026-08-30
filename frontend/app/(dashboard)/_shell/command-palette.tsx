'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import type { Route } from 'next';
import { MENUS } from './nav';
import styles from './shell.module.css';

type PaletteItem = {
  section: string;
  group: string;
  label: string;
  href: string;
};

function collectNavItems(): PaletteItem[] {
  const items: PaletteItem[] = [];
  for (const menu of Object.values(MENUS)) {
    if (!menu) continue;
    for (const group of menu.groups) {
      for (const entry of group.items) {
        items.push({
          section: menu.title,
          group: group.label,
          label: entry.label,
          href: entry.href,
        });
      }
    }
  }
  return items;
}

const NAV_ITEMS = collectNavItems();

export default function CommandPalette({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [query, setQuery] = useState('');
  const [activeIndex, setActiveIndex] = useState(0);

  const results = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return NAV_ITEMS.slice(0, 12);
    return NAV_ITEMS.filter((item) =>
      `${item.section} ${item.group} ${item.label}`.toLowerCase().includes(q)
    ).slice(0, 16);
  }, [query]);

  useEffect(() => {
    if (!open) return;
    setQuery('');
    setActiveIndex(0);
    const id = window.setTimeout(() => inputRef.current?.focus(), 20);
    return () => window.clearTimeout(id);
  }, [open]);

  useEffect(() => {
    setActiveIndex(0);
  }, [query]);

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

  if (!open) return null;

  const go = (href: string) => {
    onClose();
    router.push(href as Route);
  };

  return (
    <div className={styles.paletteRoot}>
      <button type="button" className={styles.paletteBackdrop} aria-label="Close search" onClick={onClose} />
      <div className={styles.palettePanel} role="dialog" aria-modal="true" aria-label="Search tools">
        <input
          ref={inputRef}
          className={styles.paletteInput}
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search domains, keywords, reports…"
          aria-label="Search tools"
          onKeyDown={(event) => {
            if (event.key === 'ArrowDown') {
              event.preventDefault();
              setActiveIndex((index) => Math.min(index + 1, Math.max(results.length - 1, 0)));
            }
            if (event.key === 'ArrowUp') {
              event.preventDefault();
              setActiveIndex((index) => Math.max(index - 1, 0));
            }
            if (event.key === 'Enter' && results[activeIndex]) {
              event.preventDefault();
              go(results[activeIndex].href);
            }
          }}
        />
        <ul className={styles.paletteList} role="listbox">
          {results.length === 0 ? (
            <li className={styles.paletteEmpty}>No matching tools</li>
          ) : (
            results.map((item, index) => (
              <li key={`${item.section}-${item.group}-${item.label}-${item.href}`}>
                <button
                  type="button"
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
