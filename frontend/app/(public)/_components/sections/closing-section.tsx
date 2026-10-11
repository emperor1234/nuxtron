import Link from "next/link";
import type { Route } from "next";
import { ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { ClosingContent } from "../../_content/types";
import styles from "./closing-section.module.css";

const TITLE_ID = "closing-title";

export function ClosingSection({ content }: { content: ClosingContent }) {
  return (
    <section className={styles.section} aria-labelledby={TITLE_ID}>
      <div className={styles.inner}>
        <p className={styles.eyebrow}>{content.eyebrow}</p>
        <h2 id={TITLE_ID} className={styles.title}>
          <span className={styles.lead}>{content.titleLead}</span>{" "}
          <span className={styles.accent}>{content.titleAccent}</span>
        </h2>
        <div className={styles.actions}>
          <Button asChild size="lg">
            <Link href={content.primaryCta.href as Route}>
              {content.primaryCta.label}
              <ArrowRight aria-hidden="true" data-icon="inline-end" />
            </Link>
          </Button>
          <Button asChild size="lg" variant="outline">
            <Link href={content.secondaryCta.href as Route}>{content.secondaryCta.label}</Link>
          </Button>
        </div>
      </div>
    </section>
  );
}
