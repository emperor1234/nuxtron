import Image from "next/image";
import type { ProductLine } from "@/app/lib/product-line";
import styles from "./capability-preview.module.css";

type PreviewKind =
  | "ai"
  | "trend"
  | "keywords"
  | "audit"
  | "network"
  | "document"
  | "map"
  | "quadrant"
  | "report"
  | "calendar"
  | "creative"
  | "publishing"
  | "inbox"
  | "brand"
  | "repurpose"
  | "team";

const PREVIEW_KIND: Record<
  ProductLine,
  Readonly<Record<string, PreviewKind>>
> = {
  seo: {
    "ai-visibility": "ai",
    "rank-tracking": "trend",
    "keyword-research": "keywords",
    "site-audit": "audit",
    backlinks: "network",
    "content-optimisation": "document",
    local: "map",
    market: "quadrant",
    reporting: "report",
  },
  marketing: {
    calendar: "calendar",
    writing: "document",
    creative: "creative",
    publishing: "publishing",
    inbox: "inbox",
    brand: "brand",
    repurpose: "repurpose",
    analytics: "trend",
    team: "team",
  },
};

/** A decorative, Nuxtron-owned product preview, not a customer screenshot or result. */
export function CapabilityPreview({
  product,
  id,
  label,
}: {
  product: ProductLine;
  id: string;
  label: string;
}) {
  const kind = PREVIEW_KIND[product][id] ?? "report";

  return (
    <div
      className={styles.preview}
      data-product={product}
      data-kind={kind}
      aria-hidden="true"
    >
      <div className={styles.chrome}>
        <span className={styles.dots}>
          <i />
          <i />
          <i />
        </span>
        <span className={styles.address}>app.nuxtron.com / {id}</span>
        <span className={styles.sample}>Workspace preview</span>
      </div>
      <div className={styles.app}>
        <aside className={styles.rail}>
          <Image
            src="/brand/nuxtron-icon-square.svg"
            alt=""
            width={16}
            height={16}
            unoptimized
            className={styles.mark}
          />
          <i />
          <i />
          <i />
          <i />
        </aside>
        <div className={styles.canvas}>
          <div className={styles.heading}>
            <span className={styles.title}>{label}</span>
            <span className={styles.action} />
          </div>
          <Visual kind={kind} />
        </div>
      </div>
    </div>
  );
}

function Visual({ kind }: { kind: PreviewKind }) {
  switch (kind) {
    case "ai":
      return (
        <div className={styles.promptList}>
          {[0, 1, 2].map((item) => (
            <div className={styles.promptRow} key={item}>
              <i />
              <span className={styles.promptLine} />
              <span className={styles.mention} />
            </div>
          ))}
        </div>
      );
    case "trend":
      return <ChartVisual />;
    case "keywords":
      return (
        <div className={styles.keywordVisual}>
          <div className={styles.keywordChips}>
            {["wide", "short", "medium", "wide", "short"].map(
              (width, index) => (
                <i className={styles[width]} key={`${width}-${index}`} />
              ),
            )}
          </div>
          <ChartVisual compact />
        </div>
      );
    case "audit":
      return (
        <div className={styles.auditVisual}>
          <div className={styles.healthRing}>
            <i />
          </div>
          <div className={styles.issueRows}>
            {["error", "warning", "ok"].map((type) => (
              <i key={type} data-type={type} />
            ))}
          </div>
        </div>
      );
    case "network":
      return (
        <svg
          className={styles.network}
          viewBox="0 0 260 86"
          preserveAspectRatio="none"
        >
          <path d="M22 44L83 18L136 52L199 24L239 52M83 18L107 72L199 24L211 72" />
          {[22, 83, 107, 136, 199, 211, 239].map((x, index) => (
            <circle
              key={`${x}-${index}`}
              cx={x}
              cy={[44, 18, 72, 52, 24, 72, 52][index]}
              r={index === 3 ? 7 : 5}
            />
          ))}
        </svg>
      );
    case "document":
      return <DocumentVisual />;
    case "map":
      return (
        <div className={styles.mapVisual}>
          <i />
          <i />
          <i />
          <i />
          <i />
          <b />
          <b />
          <b />
        </div>
      );
    case "quadrant":
      return (
        <div className={styles.quadrant}>
          <i />
          <i />
          <i />
          <i />
          <b />
          <b />
          <b />
        </div>
      );
    case "report":
      return (
        <div className={styles.reportVisual}>
          <div className={styles.metricCards}>
            <i />
            <i />
            <i />
          </div>
          <ChartVisual compact />
        </div>
      );
    case "calendar":
      return (
        <div className={styles.calendarVisual}>
          <div className={styles.week}>
            <i />
            <i />
            <i />
            <i />
            <i />
            <i />
            <i />
          </div>
          <div className={styles.calendarGrid}>
            {Array.from({ length: 21 }, (_, index) => (
              <i key={index} data-event={index % 5 === 1 || index % 7 === 4} />
            ))}
          </div>
        </div>
      );
    case "creative":
      return (
        <div className={styles.creativeVisual}>
          <i />
          <i />
          <i />
        </div>
      );
    case "publishing":
      return (
        <div className={styles.publishVisual}>
          {[0, 1, 2].map((item) => (
            <i key={item}>
              <b />
              <span />
              <span />
            </i>
          ))}
        </div>
      );
    case "inbox":
      return (
        <div className={styles.inboxVisual}>
          {[0, 1, 2].map((item) => (
            <i key={item}>
              <b />
              <span />
              <span />
            </i>
          ))}
        </div>
      );
    case "brand":
      return (
        <div className={styles.brandVisual}>
          <div className={styles.brandSwatches}>
            <i />
            <i />
            <i />
            <i />
          </div>
          <div className={styles.typeSample}>
            <b />
            <span />
            <span />
          </div>
        </div>
      );
    case "repurpose":
      return (
        <div className={styles.repurposeVisual}>
          <i className={styles.sourceCard} />
          <span />
          <i />
          <i />
          <i />
        </div>
      );
    case "team":
      return (
        <div className={styles.teamVisual}>
          {[0, 1, 2].map((item) => (
            <i key={item}>
              <b />
              <span />
              <em />
            </i>
          ))}
        </div>
      );
  }
}

function ChartVisual({ compact = false }: { compact?: boolean }) {
  return (
    <div
      className={
        compact ? `${styles.chart} ${styles.chartCompact}` : styles.chart
      }
    >
      <svg viewBox="0 0 260 74" preserveAspectRatio="none">
        <path className={styles.chartGrid} d="M0 18H260M0 38H260M0 58H260" />
        <path
          className={styles.chartArea}
          d="M0 60L36 48L70 52L105 29L140 39L178 17L218 28L260 8V74H0Z"
        />
        <path
          className={styles.chartLine}
          d="M0 60L36 48L70 52L105 29L140 39L178 17L218 28L260 8"
        />
      </svg>
      <div className={styles.chartLabels}>
        <i />
        <i />
        <i />
        <i />
        <i />
      </div>
    </div>
  );
}

function DocumentVisual() {
  return (
    <div className={styles.documentVisual}>
      <div className={styles.docRail}>
        <i />
        <i />
        <i />
        <i />
      </div>
      <div className={styles.docPage}>
        <b />
        <i />
        <i />
        <i />
        <span />
        <i />
        <i />
      </div>
      <div className={styles.docAside}>
        <i />
        <i />
        <i />
      </div>
    </div>
  );
}
