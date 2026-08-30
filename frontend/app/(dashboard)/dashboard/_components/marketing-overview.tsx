"use client";

import { useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { apiGet, resolveSessionTenant } from "@/app/lib/api-client";
import { Card, Page, Stat, StatGrid } from "../../_ui/kit";
import styles from "../dashboard.module.css";

type HomeState = {
  loading: boolean;
  error: string;
  plan: string;
  credits: string;
  analyses: number;
  modulesReady: number;
  modulesTotal: number;
  brand: string;
  recentDomains: string[];
};

const EMPTY: HomeState = {
  loading: true,
  error: "",
  plan: "",
  credits: "",
  analyses: 0,
  modulesReady: 0,
  modulesTotal: 0,
  brand: "",
  recentDomains: [],
};

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object"
    ? (value as Record<string, unknown>)
    : null;
}

export default function MarketingOverview({
  className,
}: {
  className?: string;
}) {
  const router = useRouter();
  const [state, setState] = useState<HomeState>(EMPTY);
  const [domain, setDomain] = useState("");

  useEffect(() => {
    const tenantId = resolveSessionTenant();
    let active = true;

    async function load() {
      if (!tenantId) {
        setState({
          ...EMPTY,
          loading: false,
          error: "No workspace is attached to this session.",
        });
        return;
      }
      try {
        const [usageResult, analysesResult, modulesResult, profileResult] =
          await Promise.allSettled([
            apiGet("/billing/usage", tenantId),
            apiGet("/seo-platform/analyses?limit=20", tenantId),
            apiGet("/seo-platform/modules", tenantId),
            apiGet("/white-label/profile", tenantId),
          ]);
        if (!active) return;

        const failures = [
          usageResult,
          analysesResult,
          modulesResult,
          profileResult,
        ].filter((item) => item.status === "rejected");
        const usage =
          usageResult.status === "fulfilled" ? usageResult.value : {};
        const analyses =
          analysesResult.status === "fulfilled" ? analysesResult.value : {};
        const modules =
          modulesResult.status === "fulfilled" ? modulesResult.value : {};
        const profile =
          profileResult.status === "fulfilled" ? profileResult.value : {};

        const rawPlan = usage.plan_display ?? usage.current_plan;
        const plan = typeof rawPlan === "string" ? rawPlan : "";
        const rawCredits = usage.credit_balance;
        const credits =
          typeof rawCredits === "number" || typeof rawCredits === "string"
            ? String(rawCredits)
            : "";
        const totalAnalyses =
          typeof analyses.total === "number"
            ? analyses.total
            : Array.isArray(analyses.analyses)
              ? analyses.analyses.length
              : 0;
        const analysisList = Array.isArray(analyses.analyses)
          ? analyses.analyses
          : [];
        const recentDomains = Array.from(
          new Set(
            analysisList
              .map((item) => {
                const record = asRecord(item);
                const candidate =
                  record?.domain ??
                  record?.target ??
                  record?.website ??
                  record?.site ??
                  record?.url;
                if (typeof candidate !== "string") return "";
                return candidate
                  .replace(/^https?:\/\//, "")
                  .replace(/\/.*$/, "")
                  .trim();
              })
              .filter(Boolean),
          ),
        ).slice(0, 4);
        const moduleList = Array.isArray(modules.modules)
          ? modules.modules
          : [];
        const ready = moduleList.filter((item) => {
          const rec = asRecord(item);
          return Boolean(
            rec?.implemented && rec.backend_ready && rec.frontend_ready,
          );
        }).length;
        const whiteLabel = asRecord(profile.white_label);
        const wlProfile = asRecord(whiteLabel?.profile);
        const brand =
          typeof wlProfile?.brand_name === "string" ? wlProfile.brand_name : "";

        setState({
          loading: false,
          error:
            failures.length === 4
              ? "Workspace data is unavailable. Sign in again or retry once the API is reachable."
              : "",
          plan,
          credits,
          analyses: totalAnalyses,
          modulesReady: ready,
          modulesTotal: moduleList.length,
          brand,
          recentDomains,
        });
      } catch (ex) {
        if (!active) return;
        setState({
          ...EMPTY,
          loading: false,
          error:
            ex instanceof Error
              ? ex.message
              : "Failed to load workspace overview.",
        });
      }
    }

    void load();
    return () => {
      active = false;
    };
  }, []);

  const hasMetrics = Boolean(
    state.plan || state.credits || state.analyses || state.modulesTotal,
  );

  function analyzeDomain(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const value = domain.trim();
    if (!value) return;
    router.push(`/seo/domain-overview?domain=${encodeURIComponent(value)}`);
  }

  return (
    <Page className={`${styles.root}${className ? ` ${className}` : ""}`}>
      <section className={styles.hero} aria-labelledby="dashboard-hero-title">
        <div className={styles.heroGlow} aria-hidden="true" />
        <div className={styles.heroContent}>
          <p className={styles.eyebrow}>
            {state.brand || "Nuxtron intelligence"}
          </p>
          <h1 id="dashboard-hero-title" className={styles.heroTitle}>
            Grow your visibility from one workspace
          </h1>
          <p className={styles.heroSubtitle}>
            Analyze any domain, uncover opportunities, and turn live marketing
            data into your next action.
          </p>
          <form className={styles.analyzeForm} onSubmit={analyzeDomain}>
            <label className={styles.srOnly} htmlFor="dashboard-domain">
              Website or domain
            </label>
            <input
              id="dashboard-domain"
              value={domain}
              onChange={(event) => setDomain(event.target.value)}
              className={styles.analyzeInput}
              inputMode="url"
              autoComplete="url"
              placeholder="Enter a website or domain"
            />
            <button
              className={styles.analyzeButton}
              type="submit"
              disabled={!domain.trim()}
            >
              Analyze
            </button>
          </form>
        </div>
      </section>

      <section className={styles.monitorCard} aria-labelledby="monitor-title">
        <div className={styles.monitorHeader}>
          <div>
            <p className={styles.sectionKicker}>Monitoring</p>
            <h2 id="monitor-title" className={styles.monitorTitle}>
              Domains to watch
            </h2>
          </div>
          <Link href="/seo/history" className={styles.textLink}>
            View analysis history
          </Link>
        </div>

        <div className={styles.monitorBody}>
          <div className={styles.monitorVisual} aria-hidden="true">
            <span className={styles.visualCard}>Visibility</span>
            <span className={styles.visualScore}>{state.analyses || "—"}</span>
            <svg viewBox="0 0 160 48" role="img">
              <path
                d="M2 39C20 34 29 43 44 31S69 23 82 28s21-17 37-10 23-7 39-14"
                fill="none"
                stroke="currentColor"
                strokeWidth="3"
              />
            </svg>
          </div>
          <div className={styles.monitorCopy}>
            <h3>Track important domains in one place</h3>
            <p>
              Re-run an analysis to compare traffic, keyword, backlink, and
              authority changes over time.
            </p>
            {state.recentDomains.length ? (
              <div className={styles.domainList}>
                {state.recentDomains.map((item) => (
                  <button
                    key={item}
                    type="button"
                    onClick={() => setDomain(item)}
                    className={styles.domainChip}
                  >
                    {item}
                  </button>
                ))}
              </div>
            ) : (
              <p className={styles.emptyNote}>
                {state.loading
                  ? "Loading workspace activity…"
                  : "No analyzed domains yet. Start with your website above."}
              </p>
            )}
          </div>
          <form className={styles.addDomainForm} onSubmit={analyzeDomain}>
            <label htmlFor="monitor-domain">Add a domain</label>
            <div className={styles.addDomainRow}>
              <input
                id="monitor-domain"
                value={domain}
                onChange={(event) => setDomain(event.target.value)}
                inputMode="url"
                autoComplete="url"
                placeholder="example.com"
              />
              <button type="submit" disabled={!domain.trim()}>
                Add & analyze
              </button>
            </div>
          </form>
        </div>
      </section>

      {state.error ? (
        <Card className={styles.errorCard}>{state.error}</Card>
      ) : null}

      {!state.loading && hasMetrics ? (
        <section aria-label="Workspace summary">
          <StatGrid>
            <Stat
              label="Plan"
              value={state.plan || "—"}
              hint="From billing usage"
            />
            <Stat
              label="Credits"
              value={state.credits || "—"}
              hint="Wallet balance"
            />
            <Stat
              label="Analyses"
              value={state.analyses}
              hint="SEO platform history"
            />
            <Stat
              label="SEO modules ready"
              value={
                state.modulesTotal
                  ? `${state.modulesReady}/${state.modulesTotal}`
                  : "—"
              }
              hint="Live module registry"
            />
          </StatGrid>
        </section>
      ) : null}
    </Page>
  );
}
