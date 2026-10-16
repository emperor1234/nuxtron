"use client";

import { useState, type FormEvent } from "react";
import { RefreshCw, Search } from "lucide-react";
import { apiGet, apiSend } from "@/app/lib/platform-api";
import { Badge, Button, Callout, DataTable, EmptyState, ErrorState, Field, FormActions, Kpi, KpiGrid, Meter, Page, PageHeader, Section, type Column } from "../../_ui/kit";
import { formatDateTime, formatNumber, truncate } from "../../_ui/format";
import { useTenant } from "../../_ui/use-resource";

type Insight = {
  brand_name: string;
  total_mentions_7d: number;
  total_mentions_30d: number;
  trending_direction: string;
  visibility_score: number;
  mentions_by_engine: Record<string, number>;
  sentiment_breakdown: Record<string, number>;
  top_queries: string[];
  updated_at: string;
};
type Mention = { id: string; search_engine: string; query: string; answer_text: string; source_url?: string | null; sentiment: string; confidence: number; timestamp: string };

const SENTIMENT_TONE = { positive: "success", negative: "danger", neutral: "neutral" } as const;

export default function AnswerEngineHubPage() {
  const tenant = useTenant();
  const [brand, setBrand] = useState("");
  const [fieldError, setFieldError] = useState("");
  const [busy, setBusy] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [failure, setFailure] = useState<unknown>(null);
  const [notice, setNotice] = useState("");
  const [loaded, setLoaded] = useState("");
  const [insight, setInsight] = useState<Insight | null>(null);
  const [mentions, setMentions] = useState<Mention[]>([]);

  async function load(name: string) {
    setBusy(true);
    setFailure(null);
    try {
      const encoded = encodeURIComponent(name);
      const [summary, rows] = await Promise.all([
        apiGet<Insight>(`/api/v1/answer-engine/insights/${encoded}`, tenant),
        apiGet<Mention[]>(`/api/v1/answer-engine/insights/${encoded}/mentions?limit=100`, tenant),
      ]);
      setInsight(summary);
      setMentions(rows);
      setLoaded(name);
    } catch (error) {
      setFailure(error);
    } finally {
      setBusy(false);
    }
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    const name = brand.trim();
    if (name.length < 2) return setFieldError("Enter the brand name to look up.");
    setFieldError("");
    setNotice("");
    void load(name);
  }

  async function sync() {
    setSyncing(true);
    setFailure(null);
    try {
      await apiSend(`/api/v1/answer-engine/sync/${encodeURIComponent(loaded)}`, "POST", undefined, tenant);
      setNotice("Sync started. AI engines are being asked about your brand. Refresh in a minute.");
    } catch (error) {
      setFailure(error);
    } finally {
      setSyncing(false);
    }
  }

  const columns: Column<Mention>[] = [
    { key: "engine", header: "Engine", strong: true, render: (row) => row.search_engine, sortValue: (row) => row.search_engine },
    { key: "query", header: "Question asked", render: (row) => truncate(row.query, 80) },
    { key: "answer", header: "Answer", render: (row) => truncate(row.answer_text, 140) },
    { key: "sentiment", header: "Sentiment", render: (row) => <Badge tone={SENTIMENT_TONE[row.sentiment as keyof typeof SENTIMENT_TONE] ?? "neutral"}>{row.sentiment}</Badge>, sortValue: (row) => row.sentiment },
    { key: "when", header: "Checked", render: (row) => formatDateTime(row.timestamp), sortValue: (row) => row.timestamp },
  ];

  return (
    <Page width="wide">
      <PageHeader title="Answer Engine Hub" subtitle="See how ChatGPT, Gemini, Perplexity and Claude talk about your brand. Mentions come from questions Nuxtron asks each engine." />
      <form onSubmit={submit} noValidate aria-label="Brand lookup" style={{ display: "flex", gap: 12, alignItems: "flex-start", flexWrap: "wrap" }}>
        <div style={{ flex: "1 1 280px", maxWidth: 420 }}><Field label="Brand name" value={brand} error={fieldError} maxLength={80} onChange={(event) => setBrand(event.target.value)} /></div>
        <div style={{ paddingTop: 24 }}><Button type="submit" variant="primary" loading={busy} icon={<Search size={15} aria-hidden="true" />}>Look up</Button></div>
      </form>
      {failure ? <ErrorState error={failure} title="The request failed" /> : null}
      {notice ? <Callout tone="success">{notice}</Callout> : null}
      {insight ? (
        <>
          <FormActions><Button loading={syncing} icon={<RefreshCw size={15} aria-hidden="true" />} onClick={() => void sync()}>Check AI engines now</Button><Button onClick={() => void load(loaded)}>Refresh</Button></FormActions>
          {insight.total_mentions_30d === 0 ? (
            <EmptyState title={`No saved mentions for ${insight.brand_name}`} description="Run a check to ask the connected AI engines about this brand. An engine only answers when its API key is configured on the server." />
          ) : (
            <>
              <KpiGrid>
                <Kpi label="Visibility score" value={`${Math.round(insight.visibility_score)}`} hint="0 to 100" />
                <Kpi label="Mentions, 7 days" value={formatNumber(insight.total_mentions_7d)} />
                <Kpi label="Mentions, 30 days" value={formatNumber(insight.total_mentions_30d)} hint={`Trend: ${insight.trending_direction}`} />
              </KpiGrid>
              <Section title="By engine">
                <div style={{ display: "grid", gap: 10, maxWidth: 520 }}>
                  {Object.entries(insight.mentions_by_engine).map(([engine, count]) => <Meter key={engine} label={engine} value={count} max={Math.max(...Object.values(insight.mentions_by_engine), 1)} tone="brand" />)}
                </div>
              </Section>
              <Section title="Mentions"><DataTable columns={columns} rows={mentions} getKey={(row) => row.id} caption="Brand mentions" pageSize={15} /></Section>
            </>
          )}
        </>
      ) : !busy && !failure ? <EmptyState title="Look up a brand" description="Enter a brand name to see saved AI answer mentions." /> : null}
    </Page>
  );
}
