"use client";

import { useEffect, useMemo, useState, type ComponentRef } from "react";
import { useRef } from "react";
import Link from "next/link";
import type { Route } from "next";
import { ArrowRight, Search, X } from "lucide-react";
import { PRODUCT_META, productAuthHref } from "@/app/lib/product-line";
import {
  FEATURE_JOBS,
  FEATURE_TOOLS,
  filterTools,
  type FeatureJob,
  type FeatureTool,
  type ProductFilter,
} from "../_content/features";
import { AnimatedIcon } from "../_components/sections/animated-icon";
import { SectionIconGlyph } from "../_components/sections/icon";
import styles from "./features.module.css";

const PRODUCT_TABS: readonly { id: ProductFilter; label: string }[] = [
  { id: "all", label: "All" },
  { id: "seo", label: PRODUCT_META.seo.label },
  { id: "marketing", label: PRODUCT_META.marketing.label },
];

function productLabel(tool: FeatureTool): string {
  if (tool.product === "both") return "SEO · Marketing";
  return PRODUCT_META[tool.product].label;
}

function startHref(tool: FeatureTool, filter: ProductFilter): string {
  if (tool.product !== "both") return productAuthHref("/register", tool.product);
  return filter === "all" ? "/register" : productAuthHref("/register", filter);
}

/**
 * Feature directory: tools grouped by job, filterable by product and text.
 * Filter state lives in the URL (?product=&q=) so any view can be shared;
 * the server renders the initial view from the same parameters.
 */
export function FeaturesExplorer({
  initialProduct,
  initialQuery,
}: {
  initialProduct: ProductFilter;
  initialQuery: string;
}) {
  const [product, setProduct] = useState<ProductFilter>(initialProduct);
  const [query, setQuery] = useState(initialQuery);
  const [activeJob, setActiveJob] = useState<FeatureJob>("research");
  const sections = useRef(new Map<FeatureJob, ComponentRef<"section">>());

  const visible = useMemo(() => filterTools(FEATURE_TOOLS, product, query), [product, query]);
  const byJob = useMemo(() => {
    const groups = new Map<FeatureJob, FeatureTool[]>();
    for (const tool of visible) groups.set(tool.job, [...(groups.get(tool.job) ?? []), tool]);
    return groups;
  }, [visible]);

  // Keep the URL in step with the filters (replace, not push: filtering is
  // not navigation, and Back should leave the page).
  useEffect(() => {
    const url = new URL(window.location.href);
    if (product === "all") url.searchParams.delete("product");
    else url.searchParams.set("product", product);
    if (query.trim()) url.searchParams.set("q", query.trim());
    else url.searchParams.delete("q");
    window.history.replaceState(window.history.state, "", url);
  }, [product, query]);

  // Highlight the job whose section has scrolled past the control bar: the
  // last section whose top is above the line just under the sticky bar.
  useEffect(() => {
    let frame = 0;
    const update = () => {
      frame = 0;
      const line = 280;
      let current: FeatureJob | null = null;
      for (const job of FEATURE_JOBS) {
        const element = sections.current.get(job.id);
        if (element && element.getBoundingClientRect().top <= line) current = job.id;
      }
      setActiveJob(current ?? FEATURE_JOBS.find((job) => sections.current.has(job.id))?.id ?? "research");
    };
    const onScroll = () => {
      if (!frame) frame = requestAnimationFrame(update);
    };
    update();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => {
      window.removeEventListener("scroll", onScroll);
      if (frame) cancelAnimationFrame(frame);
    };
  }, [byJob]);

  return (
    <>
      <div className={styles.controls}>
        <div className={styles.controlsInner}>
          <nav aria-label="Jump to a job" className={styles.jobs}>
            {FEATURE_JOBS.map((job) => {
              const count = byJob.get(job.id)?.length ?? 0;
              return (
                <a
                  key={job.id}
                  href={`#${job.id}`}
                  className={styles.job}
                  aria-current={activeJob === job.id ? "true" : undefined}
                  data-empty={count === 0 || undefined}
                >
                  {job.title}
                  <span className={styles.jobCount}>{count}</span>
                </a>
              );
            })}
          </nav>
          <div className={styles.filters}>
            <div role="radiogroup" aria-label="Filter by product" className={styles.segment}>
              {PRODUCT_TABS.map((tab) => (
                <button
                  key={tab.id}
                  type="button"
                  role="radio"
                  aria-checked={product === tab.id}
                  className={styles.segmentButton}
                  onClick={() => setProduct(tab.id)}
                >
                  {tab.label}
                </button>
              ))}
            </div>
            <label className={styles.search}>
              <Search size={16} aria-hidden="true" />
              <span className={styles.srOnly}>Search tools</span>
              <input
                type="search"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Search tools"
                className={styles.searchInput}
              />
              {query ? (
                <button type="button" className={styles.clear} onClick={() => setQuery("")} aria-label="Clear search">
                  <X size={14} aria-hidden="true" />
                </button>
              ) : null}
            </label>
          </div>
        </div>
      </div>

      <p className={styles.srOnly} aria-live="polite">
        {`${visible.length} tool${visible.length === 1 ? "" : "s"} shown`}
      </p>

      {visible.length === 0 ? (
        <div className={styles.empty}>
          <p className={styles.emptyTitle}>No tools match “{query.trim()}”.</p>
          <p className={styles.emptyBody}>Try a broader word, or clear the filters to see all {FEATURE_TOOLS.length} tools.</p>
          <button
            type="button"
            className={styles.emptyReset}
            onClick={() => {
              setQuery("");
              setProduct("all");
            }}
          >
            Clear filters
          </button>
        </div>
      ) : null}

      {FEATURE_JOBS.map((job) => {
        const tools = byJob.get(job.id);
        if (!tools?.length) return null;
        return (
          <section
            key={job.id}
            id={job.id}
            data-job={job.id}
            ref={(element) => {
              if (element) sections.current.set(job.id, element);
              else sections.current.delete(job.id);
            }}
            className={styles.group}
            aria-labelledby={`${job.id}-title`}
          >
            <header className={styles.groupHead}>
              <span className={styles.groupIcon}>
                <SectionIconGlyph name={job.icon} size={18} />
              </span>
              <div>
                <h2 id={`${job.id}-title`} className={styles.groupTitle}>
                  {job.title}
                  <span className={styles.groupCount}>{tools.length}</span>
                </h2>
                <p className={styles.groupSummary}>{job.summary}</p>
              </div>
            </header>
            <ul className={styles.grid}>
              {tools.map((tool) => (
                <li key={tool.id} className={styles.card} data-icon-host>
                  <div className={styles.cardTop}>
                    <AnimatedIcon name={tool.icon} />
                    <span className={styles.badge} data-product={tool.product}>
                      {productLabel(tool)}
                    </span>
                  </div>
                  <h3 className={styles.toolName}>{tool.name}</h3>
                  <p className={styles.toolBody}>{tool.description}</p>
                  <Link href={startHref(tool, product) as Route} className={styles.toolLink}>
                    Get started <ArrowRight size={15} aria-hidden="true" />
                  </Link>
                </li>
              ))}
            </ul>
          </section>
        );
      })}
    </>
  );
}
