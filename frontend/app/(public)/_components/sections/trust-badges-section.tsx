import { ExternalLink } from "lucide-react";
import type { TrustBadge, TrustContent } from "../../_content/types";
import { Reveal } from "../reveal";
import styles from "./trust-badges-section.module.css";

const HEADING_ID = "home-trust-title";

/**
 * Keeps only awards that are `verified` and link to an https page proving
 * them. Anything else is dropped rather than shown unproven.
 */
export function verifiedTrustBadges(badges: readonly TrustBadge[]): TrustBadge[] {
  return badges.filter(
    (badge) => (badge.verified as unknown) === true && isHttpsUrl(badge.url),
  );
}

/**
 * Third-party award tiles (e.g. a review-site report). Renders nothing when
 * there is no verified award, so the page never shows placeholder badges.
 *
 * These are deliberately plain text tiles. Do not draw or imitate an issuer's
 * badge artwork or logo. When Nuxtron receives a real award, the issuer (G2,
 * for example) provides an official embed through its vendor portal — usually
 * a hosted <img> or <script> snippet tied to the award. To use it:
 *   1. Add the award to `trust.badges` in the homepage content with
 *      `verified: true` and the issuer's public award page as `url`.
 *   2. Replace the tile body in `BadgeTile` for that issuer with the
 *      official embed markup, served from the issuer's domain exactly as
 *      supplied (no redrawing, recolouring or cropping).
 *   3. Allow the issuer's image/script host in the CSP (next.config) so
 *      the embed loads.
 */
export function TrustBadgesSection({ content }: { content: TrustContent }) {
  const badges = verifiedTrustBadges(content.badges);
  if (badges.length === 0) return null;

  return (
    <section className={styles.section} aria-labelledby={HEADING_ID}>
      <Reveal className={styles.layout}>
        <h2 id={HEADING_ID} className={styles.title}>
          {content.title}
        </h2>
        <ul className={styles.badges}>
          {badges.map((badge) => (
            <li key={badge.id}>
              <BadgeTile badge={badge} />
            </li>
          ))}
        </ul>
      </Reveal>
    </section>
  );
}

function BadgeTile({ badge }: { badge: TrustBadge }) {
  return (
    <a className={styles.tile} href={badge.url} target="_blank" rel="noopener noreferrer">
      <span className={styles.issuer}>{badge.issuer}</span>
      <span className={styles.name}>{badge.name}</span>
      <span className={styles.season}>
        {badge.season}
        <ExternalLink size={13} strokeWidth={1.8} aria-hidden="true" />
      </span>
      <span className="sr-only"> (opens the issuer&apos;s award page in a new tab)</span>
    </a>
  );
}

function isHttpsUrl(value: string): boolean {
  try {
    return new URL(value).protocol === "https:";
  } catch {
    return false;
  }
}
