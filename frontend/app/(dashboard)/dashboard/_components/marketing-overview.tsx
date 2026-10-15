"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ArrowUpRight,
  Search,
  Globe2,
  FileText,
  CalendarDays,
  Users,
  ArrowRight,
  RefreshCw,
} from "lucide-react";
import { apiGet, resolveSessionTenant } from "@/app/lib/api-client";
import NumberTicker from "./number-ticker";
import {
  Button,
  Card,
  DataStatus,
  Page,
  PageHeader,
  Stat,
  StatGrid,
  type DataStatusState,
} from "../../_ui/kit";
import styles from "../dashboard.module.css";

type Summary = {
  state: DataStatusState;
  plan: string | null;
  credits: number | null;
  analyses: number | null;
  tools: number | null;
  domains: string[];
  activityAvailable: boolean;
  failed: string[];
};
const empty: Summary = {
  state: "unavailable",
  plan: null,
  credits: null,
  analyses: null,
  tools: null,
  domains: [],
  activityAvailable: false,
  failed: [],
};
const shortcuts = [
  {
    title: "Search & visibility",
    description: "Research domains, keywords, and AI answers.",
    href: "/seo",
    icon: Search,
  },
  {
    title: "Content workspace",
    description: "Develop your next brief, draft, or campaign.",
    href: "/content-generation",
    icon: FileText,
  },
  {
    title: "Social calendar",
    description: "Plan content across your connected channels.",
    href: "/studio/social-studio/calendar",
    icon: CalendarDays,
  },
  {
    title: "Customer relationships",
    description: "Keep contacts, conversations, and deals together.",
    href: "/crm",
    icon: Users,
  },
] as const;
function record(value: unknown): Record<string, unknown> {
  return value && typeof value === "object"
    ? (value as Record<string, unknown>)
    : {};
}
function count(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) && value >= 0
    ? value
    : null;
}

export default function MarketingOverview({
  className,
}: {
  className?: string;
}) {
  const router = useRouter();
  const [summary, setSummary] = useState<Summary>(empty);
  const [loading, setLoading] = useState(true);
  const [refresh, setRefresh] = useState(0);
  const [domain, setDomain] = useState("");
  const [domainError, setDomainError] = useState("");
  const domainInput = useRef<HTMLInputElement>(null);
  useEffect(() => {
    const tenant = resolveSessionTenant();
    let active = true;
    async function load() {
      setLoading(true);
      if (!tenant) {
        setSummary({ ...empty, failed: ["Workspace session"] });
        setLoading(false);
        return;
      }
      const results = await Promise.allSettled([
        apiGet("/billing/usage", tenant),
        apiGet("/seo-platform/analyses?limit=20", tenant),
        apiGet("/seo-platform/modules", tenant),
      ]);
      if (!active) return;
      const usage = results[0].status === "fulfilled" ? results[0].value : {};
      const analysis =
        results[1].status === "fulfilled" ? results[1].value : {};
      const modules = results[2].status === "fulfilled" ? results[2].value : {};
      const list = Array.isArray(analysis.analyses) ? analysis.analyses : null;
      const moduleList = Array.isArray(modules.modules)
        ? modules.modules
        : null;
      const plan = usage.plan_display ?? usage.current_plan;
      const credits =
        typeof usage.credit_balance === "string" && usage.credit_balance.trim()
          ? Number(usage.credit_balance)
          : usage.credit_balance;
      const domains = Array.from(
        new Set(
          (list || [])
            .map((item) => {
              const entry = record(item);
              const value =
                entry.domain ??
                entry.target ??
                entry.website ??
                entry.site ??
                entry.url;
              if (typeof value !== "string") return "";
              try {
                const url = new URL(
                  /^https?:\/\//i.test(value) ? value : `https://${value}`,
                );
                return url.hostname;
              } catch {
                return "";
              }
            })
            .filter(Boolean),
        ),
      ).slice(0, 6);
      const valid = [
        typeof plan === "string" || count(credits) !== null,
        list !== null,
        moduleList !== null,
      ];
      const failed = valid.flatMap((available, index) =>
        available
          ? []
          : [
              ["Billing usage", "Analysis history", "Tool availability"][
                index
              ]!,
            ],
      );
      const preview = [usage, analysis, modules].some(
        (payload) =>
          payload.is_mock === true ||
          payload.mock === true ||
          payload.preview === true ||
          payload.is_demo === true ||
          ["mock", "demo", "sample", "preview", "fallback", "seeded"].includes(
            String(
              payload.data_source ?? payload.source ?? payload.mode ?? "",
            ).toLowerCase(),
          ),
      );
      const state: DataStatusState = !valid.every(Boolean)
        ? "unavailable"
        : preview
          ? "preview"
          : "live";
      setSummary({
        state,
        plan: typeof plan === "string" ? plan : null,
        credits: count(credits),
        analyses: count(analysis.total) ?? (list ? list.length : null),
        tools: moduleList
          ? moduleList.filter((item) => {
              const value = record(item);
              return (
                value.implemented && value.backend_ready && value.frontend_ready
              );
            }).length
          : null,
        domains,
        activityAvailable: list !== null,
        failed,
      });
      setLoading(false);
    }
    void load();
    return () => {
      active = false;
    };
  }, [refresh]);
  function analyze(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      const value = domain.trim();
      const url = new URL(
        /^https?:\/\//i.test(value) ? value : `https://${value}`,
      );
      if (
        !["http:", "https:"].includes(url.protocol) ||
        !url.hostname.includes(".") ||
        /\s/.test(value) ||
        url.username ||
        url.password
      )
        throw new Error("invalid");
      setDomainError("");
      router.push(
        `/seo/domain-overview?domain=${encodeURIComponent(url.hostname)}`,
      );
    } catch {
      setDomainError("Enter a valid domain, such as example.com.");
      domainInput.current?.focus();
    }
  }
  const number = (value: number | null) => {
    if (loading) return "…";
    if (value === null) return "—";
    const decimals =
      new Intl.NumberFormat("en-US", { maximumFractionDigits: 3 })
        .format(value)
        .split(".")[1]?.length ?? 0;
    return <NumberTicker value={value} decimals={decimals} durationMs={200} />;
  };
  return (
    <Page className={`${styles.overview} ${className || ""}`}>
      <PageHeader
        title="Workspace overview"
        subtitle="Your tools, recent research, and next steps."
        actions={
          <Button
            onClick={() => setRefresh((value) => value + 1)}
            disabled={loading}
          >
            <RefreshCw size={14} aria-hidden="true" />
            {loading ? "Refreshing…" : "Refresh"}
          </Button>
        }
      />
      {!loading && (summary.failed.length === 0 || summary.failed.length === 3) && (
        <DataStatus state={summary.state} />
      )}
      <section aria-label="Workspace summary" aria-busy={loading}>
        <StatGrid>
          <Stat
            label="Current plan"
            value={loading ? "…" : summary.plan || "—"}
            hint="Workspace subscription"
          />
          <Stat
            label="Available credits"
            value={number(summary.credits)}
            hint="Your current balance"
          />
          <Stat
            label="Domain analyses"
            value={number(summary.analyses)}
            hint="Saved research"
          />
          <Stat
            label="Available tools"
            value={number(summary.tools)}
            hint="Ready in your workspace"
          />
        </StatGrid>
      </section>
      {summary.failed.length > 0 && !loading && (
        <div className={styles.notice} role="status">
          <div>
            <strong>Some workspace data couldn’t load</strong>
            <p>
              {summary.failed.join(", ")}{" "}
              {summary.failed.length === 1 ? "is" : "are"} unavailable. Missing
              values are shown as a dash.
            </p>
          </div>
          <Button onClick={() => setRefresh((value) => value + 1)}>
            Retry
          </Button>
        </div>
      )}
      <div className={styles.workGrid}>
        <Card className={styles.analysisCard}>
          <div className={styles.sectionLabel}>
            <Search size={16} aria-hidden="true" /> DOMAIN RESEARCH
          </div>
          <h2>Start with your website.</h2>
          <p>
            Explore your search presence and find the next opportunity to
            investigate.
          </p>
          <form onSubmit={analyze} className={styles.domainForm}>
            <label htmlFor="dashboard-domain">Website or domain</label>
            <div className={styles.domainControls}>
              <input
                ref={domainInput}
                id="dashboard-domain"
                value={domain}
                onChange={(event) => {
                  setDomain(event.target.value);
                  if (domainError) setDomainError("");
                }}
                inputMode="url"
                autoComplete="url"
                placeholder="example.com"
                aria-invalid={Boolean(domainError)}
                aria-describedby={domainError ? "domain-error" : undefined}
                required
              />
              <Button variant="primary" type="submit" disabled={!domain.trim()}>
                Analyze <ArrowRight size={14} aria-hidden="true" />
              </Button>
            </div>
            {domainError && (
              <p id="domain-error" className={styles.fieldError} role="alert">
                {domainError}
              </p>
            )}
          </form>
        </Card>
        <Card className={styles.nextCard}>
          <span className={styles.sectionLabel}>MAKE IT YOUR WORKSPACE</span>
          <h2>Bring your context together.</h2>
          <p>
            Set up your brand and connect your channels to get more from your
            tools.
          </p>
          <Link href="/studio/brands">
            Set up your brand <ArrowUpRight size={16} aria-hidden="true" />
          </Link>
          <Link href="/studio/social-studio/accounts">
            Connect social accounts{" "}
            <ArrowUpRight size={16} aria-hidden="true" />
          </Link>
          <Link href="/account">
            Account overview <ArrowUpRight size={16} aria-hidden="true" />
          </Link>
        </Card>
      </div>
      <section>
        <div className={styles.sectionHeading}>
          <div>
            <h2>Pick up the work</h2>
            <p>Go straight to the tools you need.</p>
          </div>
        </div>
        <div className={styles.shortcutGrid}>
          {shortcuts.map(({ title, description, href, icon: Icon }) => (
            <Link key={href} href={href} className={styles.shortcut}>
              <Icon size={20} strokeWidth={1.6} aria-hidden="true" />
              <h3>{title}</h3>
              <p>{description}</p>
              <ArrowUpRight
                className={styles.shortcutArrow}
                size={15}
                aria-hidden="true"
              />
            </Link>
          ))}
        </div>
      </section>
      <Card pad={false}>
        <div className={styles.activityHead}>
          <div>
            <h2>Recent domains</h2>
            <p>Your latest analysis history.</p>
          </div>
          <Link href="/seo/history">
            View all <ArrowUpRight size={14} aria-hidden="true" />
          </Link>
        </div>
        {loading ? (
          <p role="status" className={styles.emptyState}>
            Loading recent research…
          </p>
        ) : !summary.activityAvailable ? (
          <div className={styles.emptyState}>
            <Globe2 size={24} aria-hidden="true" />
            <h3>History is unavailable</h3>
            <p>Retry to load your saved research.</p>
          </div>
        ) : summary.domains.length ? (
          <ul className={styles.domainList}>
            {summary.domains.map((item) => (
              <li key={item}>
                <Globe2 size={16} aria-hidden="true" />
                <Link
                  href={`/seo/domain-overview?domain=${encodeURIComponent(item)}`}
                >
                  {item}
                  <span>
                    Open analysis <ArrowUpRight size={14} aria-hidden="true" />
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        ) : (
          <div className={styles.emptyState}>
            <Globe2 size={24} aria-hidden="true" />
            <h3>Your research starts here</h3>
            <p>
              Analyze a website above. Your recent domains will appear here.
            </p>
            <Button onClick={() => domainInput.current?.focus()}>
              Analyze your first domain
            </Button>
          </div>
        )}
      </Card>
    </Page>
  );
}
