"use client";

import { useState } from "react";
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

type SeoAiKeywordOpportunity = {
  keyword?: string;
  intent?: string;
  priority?: string;
};

type SeoAiAction = {
  issue?: string;
  impact?: string;
  fix?: string;
};

type SeoAiContentPriority = {
  topic?: string;
  reason?: string;
  expected_lift?: string;
};

type SeoAiResult = {
  analysis_id?: string;
  seo_ai_score?: number;
  analysis_mode?: "llm" | "heuristic";
  ai_available?: boolean;
  cached?: boolean;
  fallback?: boolean;
  keyword_opportunities?: SeoAiKeywordOpportunity[];
  content_priorities?: SeoAiContentPriority[];
  technical_priorities?: SeoAiAction[];
  serp_strategy?: {
    primary_surface?: string;
    ctr_focus?: string;
    snippet_angle?: string;
  };
  next_actions?: string[];
  page_signals?: {
    url?: string;
    fetch_ok?: boolean;
    status_code?: number;
  };
};

export default function SeoAiCorePage() {
  const [domain, setDomain] = useState("");
  const [primaryKeyword, setPrimaryKeyword] = useState("");
  const [businessGoal, setBusinessGoal] = useState("growth");
  const [contentExcerpt, setContentExcerpt] = useState("");
  const [notes, setNotes] = useState("");
  const [result, setResult] = useState<SeoAiResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function run() {
    if (!domain.trim() || !primaryKeyword.trim()) {
      setError("Domain and primary keyword are required.");
      return;
    }
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const data = await apiSend<SeoAiResult>(
        "/seo-platform/seo-ai/analyze",
        "POST",
        {
          domain: domain.trim(),
          primary_keyword: primaryKeyword.trim(),
          business_goal: businessGoal.trim(),
          content_excerpt: contentExcerpt.trim(),
          notes: notes.trim(),
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
          : "SEO-AI analysis failed",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <Page className={styles.page}>
      <PageHeader
        title="AI Visibility"
        subtitle="Research competitors and prompts, strengthen brand visibility, and turn search signals into a focused plan."
      />

      <Card>
        <div className={styles.formCard}>
          <div className={styles.formGrid}>
            <Field
              id="seo-ai-domain"
              label="Domain"
              value={domain}
              onChange={(event) => setDomain(event.target.value)}
              placeholder="example.com"
              required
            />
            <Field
              id="seo-ai-keyword"
              label="Primary keyword"
              value={primaryKeyword}
              onChange={(event) => setPrimaryKeyword(event.target.value)}
              placeholder="best crm for startups"
              required
            />
          </div>
          <Field
            id="seo-ai-goal"
            label="Business goal"
            value={businessGoal}
            onChange={(event) => setBusinessGoal(event.target.value)}
            placeholder="Increase qualified organic demand"
          />
          <div className={styles.formGrid}>
            <div className={styles.field}>
              <label htmlFor="seo-ai-excerpt">Content excerpt</label>
              <textarea
                id="seo-ai-excerpt"
                className={styles.textarea}
                value={contentExcerpt}
                onChange={(event) => setContentExcerpt(event.target.value)}
                placeholder="Paste the current landing page or article excerpt"
              />
            </div>
            <div className={styles.field}>
              <label htmlFor="seo-ai-notes">Context and constraints</label>
              <textarea
                id="seo-ai-notes"
                className={styles.textarea}
                value={notes}
                onChange={(event) => setNotes(event.target.value)}
                placeholder="Seasonality, audience, market, or SERP pressure"
              />
            </div>
          </div>
          <div className={styles.actions}>
            <Button
              variant="primary"
              onClick={() => void run()}
              disabled={loading}
            >
              {loading ? "Building strategy…" : "Analyze AI visibility"}
            </Button>
          </div>
        </div>
      </Card>

      {error ? <div className={styles.error}>{error}</div> : null}

      {!result && !loading && !error ? (
        <Card className={styles.empty}>
          <h2>Build an AI-search strategy</h2>
          <p>
            Start with a domain and priority query. Nuxtron will organize
            keyword, content, technical, and SERP opportunities without
            presenting fallback data as live AI output.
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
            {result.page_signals?.fetch_ok === false ? (
              <Badge tone="danger">Homepage could not be crawled</Badge>
            ) : null}
          </div>

          <StatGrid>
            <Stat
              label="AI visibility score"
              value={result.seo_ai_score ?? "—"}
              hint={domain}
            />
            <Stat
              label="Keyword opportunities"
              value={result.keyword_opportunities?.length ?? 0}
            />
            <Stat
              label="Content priorities"
              value={result.content_priorities?.length ?? 0}
            />
            <Stat
              label="Technical priorities"
              value={result.technical_priorities?.length ?? 0}
            />
          </StatGrid>

          <Card>
            <div className={styles.sectionHead}>
              <CardTitle sub="How to earn attention across the current results page.">
                SERP strategy
              </CardTitle>
            </div>
            <div className={styles.strategyGrid}>
              <div className={styles.strategyItem}>
                <span>Primary surface</span>
                <strong>
                  {result.serp_strategy?.primary_surface ?? "Not available"}
                </strong>
              </div>
              <div className={styles.strategyItem}>
                <span>CTR focus</span>
                <strong>
                  {result.serp_strategy?.ctr_focus ?? "Not available"}
                </strong>
              </div>
              <div className={styles.strategyItem}>
                <span>Snippet angle</span>
                <strong>
                  {result.serp_strategy?.snippet_angle ?? "Not available"}
                </strong>
              </div>
            </div>
          </Card>

          <div className={styles.twoColumn}>
            <Card>
              <CardTitle sub="Queries worth prioritizing next.">
                Keyword opportunities
              </CardTitle>
              <ul className={styles.list}>
                {(result.keyword_opportunities ?? []).map(
                  (opportunity, index) => (
                    <li
                      className={styles.listItem}
                      key={`${opportunity.keyword}-${index}`}
                    >
                      <span>
                        <span className={styles.listTitle}>
                          {opportunity.keyword ?? "Untitled keyword"}
                        </span>
                        <br />
                        {opportunity.intent ?? "Intent unavailable"}
                      </span>
                      <Badge
                        tone={
                          opportunity.priority === "high" ? "brand" : "neutral"
                        }
                      >
                        {opportunity.priority ?? "medium"}
                      </Badge>
                    </li>
                  ),
                )}
              </ul>
            </Card>

            <Card>
              <CardTitle sub="Pages and themes with the clearest upside.">
                Content priorities
              </CardTitle>
              <ul className={styles.list}>
                {(result.content_priorities ?? []).map((priority, index) => (
                  <li
                    className={styles.listItem}
                    key={`${priority.topic}-${index}`}
                  >
                    <span>
                      <span className={styles.listTitle}>
                        {priority.topic ?? "Untitled topic"}
                      </span>
                      <br />
                      {priority.reason ?? "No rationale supplied"}
                    </span>
                    <span className={styles.listMeta}>
                      {priority.expected_lift ?? ""}
                    </span>
                  </li>
                ))}
              </ul>
            </Card>
          </div>

          <div className={styles.twoColumn}>
            <Card>
              <CardTitle sub="Issues ordered by likely search impact.">
                Technical priorities
              </CardTitle>
              <ul className={styles.list}>
                {(result.technical_priorities ?? []).map((priority, index) => (
                  <li
                    className={styles.listItem}
                    key={`${priority.issue}-${index}`}
                  >
                    <span>
                      <span className={styles.listTitle}>
                        {priority.issue ?? "Untitled issue"}
                      </span>
                      <br />
                      {priority.fix ?? "No fix supplied"}
                    </span>
                    <span className={styles.listMeta}>
                      {priority.impact ?? ""}
                    </span>
                  </li>
                ))}
              </ul>
            </Card>
            <Card>
              <CardTitle sub="A practical sequence for the next work session.">
                Next actions
              </CardTitle>
              <ul className={styles.list}>
                {(result.next_actions ?? []).map((action) => (
                  <li className={styles.listItem} key={action}>
                    <span>{action}</span>
                  </li>
                ))}
              </ul>
            </Card>
          </div>
        </>
      ) : null}
    </Page>
  );
}
