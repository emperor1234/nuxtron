"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type RefObject,
} from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { useRouter } from "next/navigation";
import type { Route } from "next";
import { isRouteVisible, useProductLine } from "@/app/lib/use-product-line";
import { ROUTE_INDEX } from "./route-index.generated";
import styles from "./shell.module.css";

type PaletteItem = {
  section: string;
  group: string;
  label: string;
  href: string;
  haystack: string;
};

const SECTION_LABELS: Record<string, string> = {
  dashboard: "Home",
  seo: "SEO",
  ai: "AI",
  traffic: "Traffic",
  local: "Local",
  content: "Content",
  social: "Social",
  studio: "Studio",
  apps: "Operations",
  settings: "Settings",
};

/**
 * Every route on disk, not just the ones someone remembered to add to the nav
 * model. The generated index is the reason this is ~240 entries rather than 57.
 */
const ITEMS: readonly PaletteItem[] = ROUTE_INDEX.filter(
  (entry) => !entry.internal,
).map((entry) => {
  const section = SECTION_LABELS[entry.section] ?? entry.section;
  return {
    section,
    group: entry.group,
    label: entry.title,
    href: entry.route,
    haystack: [
      entry.title,
      entry.group,
      section,
      entry.route,
      ...entry.keywords,
    ]
      .join(" ")
      .toLowerCase(),
  };
});

const RECENTS_KEY = "nuxtron.nav.recents";
const RECENTS_LIMIT = 6;

function readRecents(): PaletteItem[] {
  if (typeof window === "undefined") return [];
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
  if (typeof window === "undefined") return;
  try {
    const existing = readRecents().map((item) => item.href);
    const next = [href, ...existing.filter((entry) => entry !== href)].slice(
      0,
      RECENTS_LIMIT,
    );
    window.localStorage.setItem(RECENTS_KEY, JSON.stringify(next));
  } catch {
    // A full or blocked localStorage must never stop navigation.
  }
}

/**
 * Lower is better. Ranking matters far more at 240 entries than at 57: a bare
 * `includes` filter buried "Keyword Data Review" under every route whose path
 * merely contains "keyword".
 */
function score(item: PaletteItem, query: string): number {
  const label = item.label.toLowerCase();
  if (label === query) return 0;
  if (label.startsWith(query)) return 1;
  if (label.includes(query)) return 2;
  // Word-boundary hit inside the label, e.g. "audit" -> "Site Audit".
  if (
    new RegExp(`\\b${query.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}`).test(label)
  )
    return 3;
  if (item.haystack.includes(query)) return 4;
  return Number.POSITIVE_INFINITY;
}

export default function CommandPalette({
  open,
  onClose,
  returnFocusRef,
}: {
  open: boolean;
  onClose: () => void;
  returnFocusRef: RefObject<HTMLButtonElement | null>;
}) {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<globalThis.HTMLUListElement>(null);
  const [query, setQuery] = useState("");
  const [activeIndex, setActiveIndex] = useState(0);
  const [recents, setRecents] = useState<PaletteItem[]>([]);
  // A user signed in to one product never sees the other product's routes:
  // proxy.ts would only bounce them back to /dashboard.
  const product = useProductLine();
  const items = useMemo(
    () => ITEMS.filter((item) => isRouteVisible(item.href, product)),
    [product],
  );

  const visibleRecents = useMemo(
    () => recents.filter((item) => isRouteVisible(item.href, product)),
    [recents, product],
  );

  const results = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return visibleRecents.length ? visibleRecents : items.slice(0, 8);
    return items
      .map((item) => ({ item, rank: score(item, q) }))
      .filter((entry) => entry.rank !== Number.POSITIVE_INFINITY)
      .sort(
        (a, b) => a.rank - b.rank || a.item.label.length - b.item.label.length,
      )
      .slice(0, 20)
      .map((entry) => entry.item);
  }, [query, visibleRecents, items]);

  useEffect(() => {
    if (!open) return;
    const id = window.setTimeout(() => {
      setQuery("");
      setActiveIndex(0);
      setRecents(readRecents());
      inputRef.current?.focus();
    }, 20);
    return () => window.clearTimeout(id);
  }, [open]);

  // Keep the highlighted row visible when arrowing past the fold.
  useEffect(() => {
    listRef.current?.children[activeIndex]?.scrollIntoView({
      block: "nearest",
    });
  }, [activeIndex]);

  useEffect(() => {
    if (!open) return;
    const onKey = (event: globalThis.KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  const go = useCallback(
    (href: string) => {
      pushRecent(href);
      onClose();
      router.push(href as Route);
    },
    [onClose, router],
  );

  const showingRecents = !query.trim() && visibleRecents.length > 0;

  return (
    <Dialog.Root
      open={open}
      onOpenChange={(value) => {
        if (!value) onClose();
      }}
    >
      <Dialog.Portal>
        <div className={`nxScope ${styles.paletteRoot}`}>
          <Dialog.Overlay className={styles.paletteBackdrop} />
          <Dialog.Content
            className={styles.palettePanel}
            aria-describedby={undefined}
            onOpenAutoFocus={(event) => {
              event.preventDefault();
              inputRef.current?.focus();
            }}
            onCloseAutoFocus={(event) => {
              event.preventDefault();
              returnFocusRef.current?.focus();
            }}
          >
            <Dialog.Title className="sr-only">Search tools</Dialog.Title>
            <input
              ref={inputRef}
              className={styles.paletteInput}
              value={query}
              onChange={(event) => {
                setQuery(event.target.value);
                setActiveIndex(0);
              }}
              placeholder={`Search ${items.length} tools, reports and settings…`}
              aria-label="Search tools"
              role="combobox"
              aria-expanded
              aria-controls="nx-palette-list"
              aria-activedescendant={
                results[activeIndex]
                  ? `nx-palette-option-${activeIndex}`
                  : undefined
              }
              onKeyDown={(event) => {
                if (event.key === "ArrowDown") {
                  event.preventDefault();
                  setActiveIndex((index) =>
                    results.length ? (index + 1) % results.length : 0,
                  );
                }
                if (event.key === "ArrowUp") {
                  event.preventDefault();
                  setActiveIndex((index) =>
                    results.length
                      ? (index - 1 + results.length) % results.length
                      : 0,
                  );
                }
                if (event.key === "Home") {
                  event.preventDefault();
                  setActiveIndex(0);
                }
                if (event.key === "End") {
                  event.preventDefault();
                  setActiveIndex(Math.max(results.length - 1, 0));
                }
                if (event.key === "Enter" && results[activeIndex]) {
                  event.preventDefault();
                  go(results[activeIndex].href);
                }
              }}
            />
            {showingRecents ? (
              <p className={styles.paletteHint}>Recent</p>
            ) : null}
            <ul
              className={styles.paletteList}
              id="nx-palette-list"
              ref={listRef}
              role="listbox"
              aria-label="Results"
            >
              {results.length === 0 ? (
                <li role="presentation" className={styles.paletteEmpty}>
                  No tool matches “{query.trim()}”
                </li>
              ) : (
                results.map((item, index) => (
                  <li key={item.href} role="presentation">
                    <button
                      type="button"
                      id={`nx-palette-option-${index}`}
                      tabIndex={-1}
                      role="option"
                      aria-selected={index === activeIndex}
                      className={`${styles.paletteItem} ${index === activeIndex ? styles.paletteItemActive : ""}`}
                      onMouseEnter={() => setActiveIndex(index)}
                      onClick={() => go(item.href)}
                    >
                      <span className={styles.paletteItemLabel}>
                        {item.label}
                      </span>
                      <span className={styles.paletteItemMeta}>
                        {item.section} / {item.group}
                      </span>
                    </button>
                  </li>
                ))
              )}
            </ul>
          </Dialog.Content>
        </div>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
