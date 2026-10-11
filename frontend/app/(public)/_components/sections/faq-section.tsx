import { ChevronDown } from "lucide-react";
import type { FaqItem } from "../../_content/types";
import { SectionHead } from "./section-head";
import styles from "./faq-section.module.css";

const TITLE_ID = "faq-title";

/** Native <details> disclosures: keyboard and screen-reader support built in. */
export function FaqSection({ items }: { items: readonly FaqItem[] }) {
  if (items.length === 0) return null;
  return (
    <section className={styles.section} aria-labelledby={TITLE_ID}>
      <div className={styles.inner}>
        <SectionHead id={TITLE_ID} eyebrow="Questions" title="Before you get started." />
        <div className={styles.list}>
          {items.map((item) => (
            <details key={item.q} className={styles.item}>
              <summary className={styles.question}>
                {item.q}
                <ChevronDown size={18} aria-hidden="true" className={styles.chevron} />
              </summary>
              <p className={styles.answer}>{item.a}</p>
            </details>
          ))}
        </div>
      </div>
    </section>
  );
}
