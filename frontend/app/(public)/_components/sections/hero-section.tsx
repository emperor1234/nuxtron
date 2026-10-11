import Link from "next/link";
import type { Route } from "next";
import { ArrowRight, Pause, Play } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { HeroContent } from "../../_content/types";
import { ProviderLogo } from "@/app/components/marketing/provider-logo";
import { HeroDashboard } from "./hero-dashboard";
import styles from "./hero-section.module.css";

/** Below this many entries the coverage strip is a static row, not a marquee. */
const MARQUEE_MIN_ITEMS = 6;

const TITLE_ID = "home-hero-title";
const COVERAGE_ID = "home-hero-coverage";

/**
 * Homepage hero. A server component: the first-paint entrance is CSS only
 * (fill-mode backwards), so the copy is in the HTML and readable without JS.
 */
export function HeroSection({ content }: { content: HeroContent }) {
  return (
    <section className={styles.hero} aria-labelledby={TITLE_ID}>
      <Backdrop />
      <div className={styles.inner}>
        <p className={styles.eyebrow}>
          <span className={styles.eyebrowDot} aria-hidden="true" />
          {content.eyebrow}
        </p>
        <h1 id={TITLE_ID} className={styles.title}>
          <span className={styles.titleLead}>
            <Highlighted text={content.headlineLead} word={content.highlight} />
          </span>{" "}
          <span className={styles.titleAccent}>
            <Highlighted text={content.headlineAccent} word={content.highlight} />
          </span>
        </h1>
        <p className={styles.intro}>{content.intro}</p>
        <div className={styles.actions}>
          <Button asChild size="lg" className={styles.primaryCta}>
            <Link href={content.primaryCta.href as Route}>
              {content.primaryCta.label}
              <ArrowRight aria-hidden="true" className={styles.ctaArrow} />
            </Link>
          </Button>
          <Button asChild size="lg" variant="outline" className={styles.secondaryCta}>
            <Link href={content.secondaryCta.href as Route}>{content.secondaryCta.label}</Link>
          </Button>
        </div>
        {content.coverage.length > 0 ? <Coverage content={content} /> : null}
      </div>
      {content.explainer ? (
        <div className={styles.stage}>
          <HeroDashboard product={content.explainer} />
        </div>
      ) : null}
    </section>
  );
}

function Coverage({ content }: { content: HeroContent }) {
  const scrolls = content.coverage.length >= MARQUEE_MIN_ITEMS;
  return (
    <div className={styles.coverage} data-marquee={scrolls}>
      <p id={COVERAGE_ID} className={styles.coverageLabel}>
        {content.coverageLabel}
      </p>
      <div className={styles.coverageRow}>
        <div className={styles.viewport}>
          <div className={styles.track}>
            <CoverageList items={content.coverage} labelledBy={COVERAGE_ID} />
            {scrolls ? <CoverageList items={content.coverage} hidden /> : null}
          </div>
        </div>
        {scrolls ? <MarqueeToggle /> : null}
      </div>
    </div>
  );
}

function CoverageList({
  items,
  labelledBy,
  hidden = false,
}: {
  items: readonly string[];
  labelledBy?: string;
  hidden?: boolean;
}) {
  return (
    <ul
      className={styles.chips}
      aria-labelledby={hidden ? undefined : labelledBy}
      aria-hidden={hidden || undefined}
      data-copy={hidden || undefined}
    >
      {items.map((item, index) => (
        <li key={`${index}:${item}`} className={styles.chip}>
          <ProviderLogo label={item} />
        </li>
      ))}
    </ul>
  );
}

/**
 * Moving content that runs longer than five seconds needs a way to stop it
 * (WCAG 2.2.2). A native checkbox keeps this a server component: CSS reads its
 * :checked state with :has() and pauses the track, no hydration needed.
 */
function MarqueeToggle() {
  return (
    <label className={styles.toggle}>
      <input type="checkbox" className={styles.toggleInput} />
      <Pause size={16} aria-hidden="true" className={styles.iconPause} />
      <Play size={16} aria-hidden="true" className={styles.iconPlay} />
      <span className={styles.toggleText}>Pause scrolling list</span>
    </label>
  );
}

/** Wraps one word of a headline line in a highlighter mark. */
function Highlighted({ text, word }: { text: string; word?: string }) {
  const at = word ? text.indexOf(word) : -1;
  if (!word || at < 0) return <>{text}</>;
  return (
    <>
      {text.slice(0, at)}
      <mark className={styles.mark}>{word}</mark>
      {text.slice(at + word.length)}
    </>
  );
}

/**
 * Decorative backdrop: lines that flow down and converge on the product shot,
 * with a soft light behind the screen. Colours come from the hero tokens in
 * hero-section.module.css so the background can be re-themed in one place.
 */
function Backdrop() {
  // Lines start spread across the top and converge into the top edge of the
  // product shot (~56% down the hero), then run straight down behind it.
  const lines = Array.from({ length: 28 }, (_, i) => {
    const t = i / 27;
    const xTop = -160 + t * 1760;
    const xEnd = 520 + t * 400;
    return `M${xTop.toFixed(1)},-20 C${xTop.toFixed(1)},300 ${xEnd.toFixed(1)},360 ${xEnd.toFixed(1)},560 L${xEnd.toFixed(1)},1000`;
  });
  return (
    <div className={styles.backdrop} aria-hidden="true">
      <svg viewBox="0 0 1440 1000" preserveAspectRatio="none" className={styles.lines}>
        {lines.map((d, i) => (
          <path key={i} d={d} className={styles.line} />
        ))}
        {[3, 9, 15, 21].map((i, n) => (
          <path key={`g${i}`} d={lines[i]} className={styles.glint} pathLength={1} style={{ animationDelay: `${n * 1.6}s` }} />
        ))}
      </svg>
      <div className={styles.glow} />
    </div>
  );
}
