import type { CSSProperties } from "react";
import Link from "next/link";
import type { Route } from "next";
import { ArrowRight, Check } from "lucide-react";
import type { ProductHubContent } from "../../_content/types";
import { Reveal } from "../reveal";
import { AnimatedIcon } from "./animated-icon";
import { SectionHead } from "./section-head";
import styles from "./product-hub-section.module.css";

const TITLE_ID = "product-hub-title";

/** One card per product area: what it is, what's in it, one way in. */
export function ProductHubSection({ content }: { content: ProductHubContent }) {
  return (
    <section className={styles.section} aria-labelledby={TITLE_ID}>
      <div className={styles.inner}>
        <SectionHead id={TITLE_ID} eyebrow={content.eyebrow} title={content.title} intro={content.intro} />
        <ul
          className={styles.grid}
          // One row of products: as many columns as cards, up to four.
          style={{ "--cols": Math.min(Math.max(content.cards.length, 1), 4) } as CSSProperties}
        >
          {content.cards.map((card, index) => (
            <li key={card.id} data-icon-host>
              <Reveal delay={Math.min(index, 3) * 0.05} className={styles.card}>
                <span className={styles.icon}>
                  <AnimatedIcon name={card.icon} tone="solid" size={22} />
                </span>
                <h3 className={styles.name}>{card.name}</h3>
                <p className={styles.tagline}>{card.tagline}</p>
                <ul className={styles.features}>
                  {card.features.map((feature) => (
                    <li key={feature}>
                      <Check size={14} aria-hidden="true" className={styles.check} />
                      {feature}
                    </li>
                  ))}
                </ul>
                <Link href={card.link.href as Route} className={styles.link}>
                  {card.link.label}
                  <ArrowRight size={15} aria-hidden="true" className={styles.arrow} />
                </Link>
              </Reveal>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
