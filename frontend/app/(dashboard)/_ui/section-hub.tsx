"use client";

import Link from "next/link";
import { useState } from "react";
import { ArrowUpRight } from "lucide-react";
import { MENUS, type RailKey } from "../_shell/nav";
import { Card, EmptyState, Page, PageHeader, SearchField } from "./kit";
import styles from "./section-hub.module.css";

/**
 * Landing page for a product section. It is built from the same navigation
 * model as the sidebar and ⌘K search, so every tool listed here is a real page
 * and the hub can never drift from the menus.
 */
export function SectionHub({ section, intro }: { section: RailKey; intro?: string }) {
  const menu = MENUS[section];
  const [query, setQuery] = useState("");
  if (!menu) return null;

  const needle = query.trim().toLowerCase();
  const groups = menu.groups
    .map((group) => ({
      ...group,
      items: needle
        ? group.items.filter((item) => `${item.label} ${item.description ?? ""}`.toLowerCase().includes(needle))
        : group.items,
    }))
    .filter((group) => group.items.length > 0);
  const total = menu.groups.reduce((sum, group) => sum + group.items.length, 0);

  return (
    <Page>
      <PageHeader title={menu.title} subtitle={intro ?? menu.summary} />
      {total > 8 ? (
        <SearchField
          value={query}
          onChange={setQuery}
          placeholder={`Search ${total} ${menu.title} tools`}
          label={`Search ${menu.title} tools`}
        />
      ) : null}
      {groups.length === 0 ? (
        <EmptyState title="No tools match your search" description="Try a different word, or clear the search to see everything." />
      ) : (
        groups.map((group) => (
          <section key={group.label} className={styles.group} aria-labelledby={`hub-${group.label}`}>
            <h2 id={`hub-${group.label}`} className={styles.groupTitle}>
              {group.label}
              <span className={styles.count}>{group.items.length}</span>
            </h2>
            <div className={styles.grid}>
              {group.items.map((item) => (
                <Link key={item.href} href={item.href} className={styles.tile}>
                  <Card className={styles.tileCard}>
                    <span className={styles.tileHead}>
                      <span className={styles.tileTitle}>{item.label}</span>
                      <ArrowUpRight size={15} aria-hidden="true" className={styles.arrow} />
                    </span>
                    {item.description ? <span className={styles.tileText}>{item.description}</span> : null}
                  </Card>
                </Link>
              ))}
            </div>
          </section>
        ))
      )}
    </Page>
  );
}
