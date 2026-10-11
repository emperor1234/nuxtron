"use client";

import { useId, useState } from "react";
import Link from "next/link";
import type { Route } from "next";
import { ArrowUpRight, Check, ChevronDown } from "lucide-react";
import type { CapabilityBlock, CapabilityContent } from "../../_content/types";
import type { ProductLine } from "@/app/lib/product-line";
import { CapabilityPreview } from "./capability-preview";
import { SectionHead } from "./section-head";
import styles from "./capability-blocks-section.module.css";

const TITLE_ID = "capabilities-title";

/**
 * Expandable capability blocks. Each block is an independent disclosure: the
 * summary is always visible, the detail opens in place. Height animates with
 * the grid-template-rows 0fr → 1fr technique so nothing is measured in JS.
 */
export function CapabilityBlocksSection({
  content,
  product,
}: {
  content: CapabilityContent;
  product: ProductLine;
}) {
  return (
    <section className={styles.section} aria-labelledby={TITLE_ID}>
      <div className={styles.inner}>
        <SectionHead
          id={TITLE_ID}
          eyebrow={content.eyebrow}
          title={content.title}
          intro={content.intro}
        />
        <ul className={styles.grid}>
          {content.blocks.map((block) => (
            <li key={block.id}>
              <Block block={block} product={product} />
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

function Block({
  block,
  product,
}: {
  block: CapabilityBlock;
  product: ProductLine;
}) {
  const [open, setOpen] = useState(false);
  const panelId = useId();
  return (
    <article className={styles.block} data-open={open}>
      <CapabilityPreview product={product} id={block.id} label={block.title} />
      <div className={styles.content}>
        <h3 className={styles.blockTitle}>{block.title}</h3>
        <p className={styles.summary}>{block.summary}</p>
        <button
          type="button"
          className={styles.toggle}
          aria-expanded={open}
          aria-controls={panelId}
          onClick={() => setOpen((value) => !value)}
        >
          {open ? "Show less" : "What's included"}
          <ChevronDown
            size={16}
            aria-hidden="true"
            className={styles.chevron}
          />
        </button>
        <div id={panelId} className={styles.detail} inert={!open}>
          <div className={styles.detailInner}>
            <ul className={styles.bullets}>
              {block.bullets.map((bullet) => (
                <li key={bullet}>
                  <Check
                    size={14}
                    aria-hidden="true"
                    className={styles.check}
                  />
                  {bullet}
                </li>
              ))}
            </ul>
            <Link href={block.link.href as Route} className={styles.link}>
              {block.link.label}
              <ArrowUpRight size={15} aria-hidden="true" />
            </Link>
          </div>
        </div>
      </div>
    </article>
  );
}
