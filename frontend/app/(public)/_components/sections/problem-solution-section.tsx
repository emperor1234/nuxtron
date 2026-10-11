import Link from "next/link";
import type { Route } from "next";
import { ArrowRight, Minus } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { ProblemSolutionContent } from "../../_content/types";
import { Reveal } from "../reveal";
import { SectionHead } from "./section-head";
import styles from "./problem-solution-section.module.css";

const TITLE_ID = "problem-solution-title";

/** Names the cost of the status quo, then the single answer to it. */
export function ProblemSolutionSection({ content }: { content: ProblemSolutionContent }) {
  return (
    <section className={styles.section} aria-labelledby={TITLE_ID}>
      <div className={styles.inner}>
        <SectionHead id={TITLE_ID} eyebrow={content.eyebrow} title={content.title} tone="ink" />
        <ul className={styles.problems}>
          {content.problems.map((problem, index) => (
            <li key={problem.title}>
              <Reveal delay={index * 0.06} className={styles.problem}>
                <span className={styles.marker} aria-hidden="true">
                  <Minus size={14} />
                </span>
                <h3 className={styles.problemTitle}>{problem.title}</h3>
                <p className={styles.problemBody}>{problem.body}</p>
              </Reveal>
            </li>
          ))}
        </ul>
        <Reveal delay={0.18} className={styles.solution}>
          <div>
            <h3 className={styles.solutionTitle}>{content.solution.title}</h3>
            <p className={styles.solutionBody}>{content.solution.body}</p>
          </div>
          <Button asChild size="lg">
            <Link href={content.solution.cta.href as Route}>
              {content.solution.cta.label}
              <ArrowRight aria-hidden="true" data-icon="inline-end" />
            </Link>
          </Button>
        </Reveal>
      </div>
    </section>
  );
}
