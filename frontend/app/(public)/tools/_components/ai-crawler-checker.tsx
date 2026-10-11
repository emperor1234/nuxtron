"use client";

import { useMemo, useState, type FormEvent } from "react";
import { ExternalLink, ScanSearch } from "lucide-react";
import {
  AI_CRAWLER_TARGETS,
  checkCrawler,
  parseRobotsTxt,
  type CrawlerCheck,
} from "../_lib/robots";
import styles from "../tools.module.css";

const SAMPLE_ROBOTS = `User-agent: *
Disallow: /private/

User-agent: GPTBot
Disallow: /

User-agent: Google-Extended
Disallow: /training-data/

User-agent: OAI-SearchBot
Allow: /
`;

export function AiCrawlerChecker() {
  const [siteUrl, setSiteUrl] = useState("");
  const [robotsText, setRobotsText] = useState("");
  const [results, setResults] = useState<CrawlerCheck[] | null>(null);
  const [error, setError] = useState("");

  const robotsFileHref = useMemo(() => {
    try {
      const parsed = new URL(siteUrl.trim());
      if (
        !["http:", "https:"].includes(parsed.protocol) ||
        parsed.username ||
        parsed.password
      )
        return null;
      return `${parsed.origin}/robots.txt`;
    } catch {
      return null;
    }
  }, [siteUrl]);

  function analyze(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setResults(null);
    if (!robotsText.trim()) {
      setError(
        "Paste the contents of a robots.txt file before checking crawler rules.",
      );
      return;
    }
    if (robotsText.length > 500_000) {
      setError("This tool accepts up to 500 KB of robots.txt text at a time.");
      return;
    }
    const parsed = parseRobotsTxt(robotsText);
    setResults(
      AI_CRAWLER_TARGETS.map((target) => checkCrawler(parsed, target)),
    );
  }

  return (
    <>
      <form className={styles.toolForm} onSubmit={analyze}>
        <div className={styles.formGrid}>
          <div className={styles.field}>
            <label className={styles.label} htmlFor="crawler-site-url">
              Website root (optional)
            </label>
            <input
              id="crawler-site-url"
              className={styles.input}
              type="url"
              inputMode="url"
              autoComplete="url"
              placeholder="https://example.com"
              value={siteUrl}
              onChange={(event) => setSiteUrl(event.target.value)}
            />
            <p className={styles.helpText}>
              Use the link to open the file yourself; this page does not fetch
              your site.
            </p>
            {robotsFileHref ? (
              <a
                className={styles.open}
                href={robotsFileHref}
                target="_blank"
                rel="noreferrer"
              >
                Open robots.txt <ExternalLink size={14} aria-hidden="true" />
              </a>
            ) : null}
          </div>
          <div className={styles.field}>
            <span className={styles.label}>How this works</span>
            <p className={styles.helpText}>
              Paste a public robots.txt file below. The checker evaluates its
              user-agent groups and sample paths entirely in this browser.
            </p>
            <p className={styles.helpText}>
              No URL is fetched and the pasted text is not submitted by this
              tool.
            </p>
          </div>
          <div className={`${styles.field} ${styles.fieldFull}`}>
            <label className={styles.label} htmlFor="robots-content">
              robots.txt content
            </label>
            <textarea
              id="robots-content"
              className={styles.textarea}
              spellCheck={false}
              maxLength={500_000}
              placeholder={
                "User-agent: *\nDisallow: /private/\n\nUser-agent: GPTBot\nDisallow: /"
              }
              value={robotsText}
              onChange={(event) => {
                setRobotsText(event.target.value);
                setResults(null);
              }}
            />
          </div>
        </div>
        <div className={styles.actionRow}>
          <button
            className={styles.secondaryButton}
            type="button"
            onClick={() => {
              setRobotsText(SAMPLE_ROBOTS);
              setResults(null);
              setError("");
            }}
          >
            Load example
          </button>
          <button
            className={styles.actionButton}
            type="submit"
            disabled={!robotsText.trim()}
          >
            <ScanSearch size={16} aria-hidden="true" />
            Check crawler rules
          </button>
        </div>
      </form>

      {error ? (
        <p className={styles.errorMessage} role="alert">
          {error}
        </p>
      ) : null}

      {results ? (
        <section
          className={styles.resultPanel}
          aria-live="polite"
          aria-labelledby="crawler-results-heading"
        >
          <h2 className={styles.resultHeading} id="crawler-results-heading">
            Results for {results.length} crawler tokens
          </h2>
          <p className={styles.resultIntro}>
            These are sample-path matches from the text you pasted—not a live
            crawlability test or a guarantee of how a service will behave.
          </p>
          <ul className={styles.resultList}>
            {results.map((result) => {
              const state =
                result.blockedCount === result.pathChecks.length
                  ? "blocked"
                  : result.blockedCount > 0
                    ? "partial"
                    : "allowed";
              const sourceLabel =
                result.source === "specific"
                  ? "Specific group"
                  : result.source === "wildcard"
                    ? "Wildcard group"
                    : "No matching group";
              return (
                <li className={styles.resultCard} key={result.target.id}>
                  <div className={styles.resultTop}>
                    <span className={styles.resultLabel}>
                      {result.target.name}{" "}
                      <span aria-label={`provider ${result.target.product}`}>
                        · {result.target.product}
                      </span>
                    </span>
                    <span className={styles.resultBadge} data-state={state}>
                      {result.headline}
                    </span>
                  </div>
                  <p className={styles.resultDetail}>{result.target.purpose}</p>
                  <p className={styles.resultDetail}>
                    Rule source: {sourceLabel}.
                  </p>
                  {result.target.note ? (
                    <p className={styles.resultDetail}>{result.target.note}</p>
                  ) : null}
                  <ul
                    className={styles.pathList}
                    aria-label={`${result.target.name} sample paths`}
                  >
                    {result.pathChecks.map((check) => (
                      <li className={styles.pathItem} key={check.path}>
                        <code>{check.path}</code>
                        <span
                          className={styles.resultBadge}
                          data-state={check.allowed ? "allowed" : "blocked"}
                        >
                          {check.allowed
                            ? "Allowed by rules"
                            : "Disallowed by rules"}
                        </span>
                      </li>
                    ))}
                  </ul>
                </li>
              );
            })}
          </ul>
        </section>
      ) : null}

      <p className={styles.disclaimer}>
        robots.txt is a crawler preference protocol, not access control. Do not
        use it to protect private data. User-directed fetchers and
        service-specific controls can behave differently from automatic
        crawlers.
      </p>
    </>
  );
}
