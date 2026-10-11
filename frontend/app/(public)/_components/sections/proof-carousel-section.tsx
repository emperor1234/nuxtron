import type { Route } from "next";
import Link from "next/link";
import { ArrowUpRight, Quote } from "lucide-react";
import type { ProofContent, ProofEntry } from "../../_content/types";
import { Reveal } from "../reveal";
import { Carousel } from "./carousel";
import styles from "./proof-carousel-section.module.css";

const HEADING_ID = "home-proof-title";

/**
 * Keeps only real, checkable customer statements: `verified` must be literally
 * true and `source` must say where the statement can be checked.
 */
export function verifiedProofEntries(entries: readonly ProofEntry[]): ProofEntry[] {
  return entries.filter(
    (entry) => (entry.verified as unknown) === true && entry.source.trim().length > 0,
  );
}

/**
 * Customer proof carousel. Renders nothing at all when there is no verified
 * entry, so the page never shows placeholder quotes.
 */
export function ProofCarouselSection({ content }: { content: ProofContent }) {
  const entries = verifiedProofEntries(content.entries);
  if (entries.length === 0) return null;

  return (
    <section className={styles.section} aria-labelledby={HEADING_ID}>
      <Reveal className={styles.heading}>
        <p className={styles.eyebrow}>
          <span aria-hidden="true" />
          {content.eyebrow}
        </p>
        <h2 id={HEADING_ID}>{content.title}</h2>
      </Reveal>
      <Reveal delay={0.06}>
        <Carousel
          label={content.title}
          slideWidth={{
            md: "calc((100% - var(--carousel-gap)) / 2)",
            lg: "calc((100% - var(--carousel-gap)) / 2)",
          }}
        >
          {entries.map((entry) => (
            <ProofSlide key={entry.id} entry={entry} />
          ))}
        </Carousel>
      </Reveal>
    </section>
  );
}

function ProofSlide({ entry }: { entry: ProofEntry }) {
  const attribution = [entry.person, entry.role, entry.company].filter(Boolean).join(" · ");
  return (
    <figure className={styles.card}>
      {entry.metric ? (
        <p className={styles.metric}>
          <strong>{entry.metric.value}</strong>
          <span>{entry.metric.label}</span>
        </p>
      ) : (
        <Quote className={styles.quoteMark} size={22} strokeWidth={1.6} aria-hidden="true" />
      )}
      <blockquote className={styles.quote}>
        <p>{entry.quote}</p>
      </blockquote>
      <figcaption className={styles.attribution}>{attribution}</figcaption>
      <SourceLink source={entry.source} person={entry.person} />
    </figure>
  );
}

/** Links the source when it is an https URL or a site path; otherwise cites it as text. */
function SourceLink({ source, person }: { source: string; person: string }) {
  const href = source.trim();
  const label = (
    <>
      Read the story
      <span className="sr-only"> from {person}</span>
      <ArrowUpRight size={15} strokeWidth={1.8} aria-hidden="true" />
    </>
  );
  if (isSitePath(href)) {
    return (
      <Link className={styles.link} href={href as Route}>
        {label}
      </Link>
    );
  }
  if (isHttpsUrl(href)) {
    return (
      <a className={styles.link} href={href} target="_blank" rel="noopener noreferrer">
        {label}
        <span className="sr-only"> (opens in a new tab)</span>
      </a>
    );
  }
  return <p className={styles.citation}>Source: {href}</p>;
}

function isSitePath(value: string): boolean {
  return value.startsWith("/") && !value.startsWith("//");
}

function isHttpsUrl(value: string): boolean {
  try {
    return new URL(value).protocol === "https:";
  } catch {
    return false;
  }
}
