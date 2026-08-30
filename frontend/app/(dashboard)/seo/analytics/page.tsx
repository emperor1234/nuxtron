"use client";

import { useState, type FormEvent } from "react";
import { resolveSessionTenant } from "@/app/lib/api-client";
import { apiSend } from "@/app/lib/platform-api";
import {
  Badge,
  Button,
  Card,
  CardTitle,
  Field,
  Page,
  PageHeader,
  Stat,
  StatGrid,
} from "../../_ui/kit";
import styles from "../components/seo-workspace.module.css";

const STRICT_NO_MOCK_FALSY = new Set(["0", "false", "no", "off"]);
const STRICT_NO_MOCK_RAW = (process.env.NEXT_PUBLIC_STRICT_NO_MOCK || "")
  .trim()
  .toLowerCase();
const IS_STRICT_NO_MOCK_MODE = STRICT_NO_MOCK_RAW
  ? !STRICT_NO_MOCK_FALSY.has(STRICT_NO_MOCK_RAW)
  : process.env.NODE_ENV === "production";

type AnalyticsResult = {
  analysis_id: string;
  report_score: number;
  domain: string;
  kpi_trends: { kpi: string; trend: string; change_pct: number }[];
  module_highlights: { module: string; impact: string; note: string }[];
  risks: string[];
  next_actions: string[];
  recommended_tools: string[];
  generated_at: string;
  cached?: boolean;
  analysis_mode?: "llm" | "heuristic";
  fallback?: boolean;
};

export default function AnalyticsReportingPage() {
  const [goal, setGoal] = useState(
    "Increase organic traffic across core product pages",
  );
  const [domain, setDomain] = useState("");
  const [primaryKeyword, setPrimaryKeyword] = useState("");
  const [market, setMarket] = useState("us");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<AnalyticsResult | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!domain.trim()) {
      setError("Enter a domain to generate an analytics report.");
      return;
    }
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const data = await apiSend<AnalyticsResult>(
        "/seo-platform/analytics/report",
        "POST",
        {
          goal: goal.trim(),
          domain: domain.trim(),
          primary_keyword: primaryKeyword.trim(),
          market: market.trim(),
        },
        resolveSessionTenant(),
      );
      if (data?.fallback === true && data?.analysis_mode !== "heuristic") {
        throw new Error(
          IS_STRICT_NO_MOCK_MODE
            ? "Live LLM backend is unavailable in strict no-mock mode."
            : "Live LLM backend is unavailable in fail-closed mode.",
        );
      }
      setResult(data);
    } catch (exception) {
      setError(
        exception instanceof Error
          ? exception.message
          : "Analytics report failed",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <Page className={styles.page}>
      <PageHeader
        title="Traffic Analytics"
        subtitle="Turn cross-channel KPI trends, risks, and opportunities into a prioritized action plan."
      />

      <Card>
        <form className={styles.formCard} onSubmit={handleSubmit}>
          <div className={styles.field}>
            <label htmlFor="analytics-goal">Business goal</label>
            <textarea
              id="analytics-goal"
              className={styles.textarea}
              value={goal}
              onChange={(event) => setGoal(event.target.value)}
              required
            />
          </div>
          <div className={styles.formGridWide}>
            <Field
              id="analytics-domain"
              label="Domain"
              value={domain}
              onChange={(event) => setDomain(event.target.value)}
              placeholder="example.com"
              required
            />
            <Field
              id="analytics-keyword"
              label="Primary keyword"
              value={primaryKeyword}
              onChange={(event) => setPrimaryKeyword(event.target.value)}
              placeholder="crm software"
            />
            <Field
              id="analytics-market"
              label="Market"
              value={market}
              onChange={(event) => setMarket(event.target.value)}
              placeholder="us"
            />
          </div>
          <div className={styles.actions}>
            <Button variant="primary" type="submit" disabled={loading}>
              {loading ? "Generating report…" : "Generate report"}
            </Button>
          </div>
        </form>
      </Card>

      {error ? <div className={styles.error}>{error}</div> : null}

      {!result && !loading && !error ? (
        <Card className={styles.empty}>
          <h2>Your traffic intelligence starts here</h2>
          <p>
            Add a real domain and goal to compare performance signals and
            receive a focused list of next actions.
          </p>
        </Card>
      ) : null}

      {result ? (
        <>
          <div className={styles.statusRow}>
            {result.analysis_mode ? (
              <Badge
                tone={result.analysis_mode === "llm" ? "success" : "neutral"}
              >
                {result.analysis_mode === "llm"
                  ? "Live AI analysis"
                  : "Heuristic analysis"}
              </Badge>
            ) : null}
            {result.cached ? <Badge tone="brand">Cached result</Badge> : null}
          </div>

          <StatGrid>
            <Stat
              label="Report score"
              value={result.report_score}
              hint={result.domain}
            />
            <Stat
              label="KPI trends"
              value={result.kpi_trends.length}
              hint="Signals evaluated"
            />
            <Stat
              label="Risks"
              value={result.risks.length}
              hint="Items needing attention"
            />
            <Stat
              label="Next actions"
              value={result.next_actions.length}
              hint="Prioritized recommendations"
            />
          </StatGrid>

          <div className={styles.twoColumn}>
            <Card>
              <CardTitle sub="Direction and percentage change by metric.">
                KPI trends
              </CardTitle>
              <ul className={styles.list}>
                {result.kpi_trends.map((trend) => (
                  <li className={styles.listItem} key={trend.kpi}>
                    <span className={styles.listTitle}>{trend.kpi}</span>
                    <span className={styles.listMeta}>
                      {trend.trend} · {trend.change_pct}%
                    </span>
                  </li>
                ))}
              </ul>
            </Card>
            <Card>
              <CardTitle sub="The highest-value work to do next.">
                Next actions
              </CardTitle>
              <ul className={styles.list}>
                {result.next_actions.map((action) => (
                  <li className={styles.listItem} key={action}>
                    <span>{action}</span>
                  </li>
                ))}
              </ul>
            </Card>
          </div>

          {result.risks.length || result.module_highlights.length ? (
            <div className={styles.twoColumn}>
              <Card>
                <CardTitle sub="Issues that could limit performance.">
                  Risks
                </CardTitle>
                <ul className={styles.list}>
                  {result.risks.map((risk) => (
                    <li className={styles.listItem} key={risk}>
                      <span>{risk}</span>
                    </li>
                  ))}
                </ul>
              </Card>
              <Card>
                <CardTitle sub="Cross-module findings with measurable impact.">
                  Highlights
                </CardTitle>
                <ul className={styles.list}>
                  {result.module_highlights.map((highlight) => (
                    <li
                      className={styles.listItem}
                      key={`${highlight.module}-${highlight.note}`}
                    >
                      <span>
                        <span className={styles.listTitle}>
                          {highlight.module}
                        </span>
                        <br />
                        {highlight.note}
                      </span>
                      <span className={styles.listMeta}>
                        {highlight.impact}
                      </span>
                    </li>
                  ))}
                </ul>
              </Card>
            </div>
          ) : null}
        </>
      ) : null}
    </Page>
  );
}
