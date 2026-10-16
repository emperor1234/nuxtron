"use client";

import { useState, type FormEvent } from "react";
import { apiGet, apiSend } from "@/app/lib/platform-api";
import { Button, Callout, Card, DataTable, EmptyState, ErrorState, Field, FieldSelect, Kpi, KpiGrid, Page, PageHeader, Section, type Column } from "../../_ui/kit";
import { formatNumber } from "../../_ui/format";
import { ResourceView, useResource, useTenant } from "../../_ui/use-resource";

type Analysis = { period_days: number; total_unique_keywords: number; total_prompt_volume: number; trending_count: number };
type Word = { word: string; count: number };
type Source = { source: string; volume: number };
type Overview = { analysis: Analysis; words: Word[]; sources: Source[] };

const SOURCES = ["chatgpt", "claude", "gemini", "perplexity", "copilot", "other"];

export default function PromptResearchPage() {
  const tenant = useTenant();
  const resource = useResource<Overview>(async (id) => {
    const [analysis, words, sources] = await Promise.all([
      apiGet<Analysis>("/api/v1/prompt-volumes/analysis", id),
      apiGet<{ top_words: Word[] }>("/api/v1/prompt-volumes/top-words", id),
      apiGet<{ sources: Source[] }>("/api/v1/prompt-volumes/sources", id),
    ]);
    return { analysis, words: words.top_words, sources: sources.sources };
  }, []);
  const [keyword, setKeyword] = useState("");
  const [source, setSource] = useState("chatgpt");
  const [error, setError] = useState("");
  const [failure, setFailure] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  async function record(event: FormEvent) {
    event.preventDefault();
    if (keyword.trim().length < 2) return setError("Enter the prompt or question.");
    setError("");
    setBusy(true);
    setFailure(null);
    try {
      await apiSend(`/api/v1/prompt-volumes/record-prompt?${new URLSearchParams({ keyword: keyword.trim(), sources: source })}`, "POST", undefined, tenant);
      setKeyword("");
      resource.reload();
    } catch (caught) {
      setFailure(caught);
    } finally {
      setBusy(false);
    }
  }

  const wordColumns: Column<Word>[] = [
    { key: "w", header: "Word", strong: true, render: (row) => row.word, sortValue: (row) => row.word },
    { key: "c", header: "Times seen", numeric: true, render: (row) => formatNumber(row.count), sortValue: (row) => row.count },
  ];
  const sourceColumns: Column<Source>[] = [
    { key: "s", header: "AI assistant", strong: true, render: (row) => row.source },
    { key: "v", header: "Prompts", numeric: true, render: (row) => formatNumber(row.volume), sortValue: (row) => row.volume },
  ];

  return (
    <Page width="wide">
      <PageHeader title="Prompt Research" subtitle="Log the questions people ask AI assistants about your category and see which words keep coming up." />
      <Card>
        <form onSubmit={record} noValidate aria-label="Log a prompt" style={{ display: "flex", gap: 12, alignItems: "flex-start", flexWrap: "wrap" }}>
          <div style={{ flex: "1 1 320px" }}><Field label="Prompt or question" value={keyword} error={error} maxLength={300} onChange={(event) => setKeyword(event.target.value)} /></div>
          <div style={{ width: 180 }}><FieldSelect label="Where you saw it" value={source} onChange={(event) => setSource(event.target.value)}>{SOURCES.map((item) => <option key={item} value={item}>{item}</option>)}</FieldSelect></div>
          <div style={{ paddingTop: 24 }}><Button type="submit" variant="primary" loading={busy}>Log prompt</Button></div>
        </form>
        {failure ? <ErrorState error={failure} title="Not saved" /> : null}
      </Card>
      <ResourceView resource={resource} isEmpty={(data) => data.analysis.total_prompt_volume === 0} empty={<EmptyState title="No prompts logged" description="Log the first prompt above. Counts reflect only what you log." />}>
        {(data) => (
          <>
            <KpiGrid>
              <Kpi label="Prompts logged" value={formatNumber(data.analysis.total_prompt_volume)} />
              <Kpi label="Distinct prompts" value={formatNumber(data.analysis.total_unique_keywords)} />
              <Kpi label="Trending" value={formatNumber(data.analysis.trending_count)} hint={`Last ${data.analysis.period_days} days`} />
            </KpiGrid>
            <Section title="Words that recur"><DataTable columns={wordColumns} rows={data.words} getKey={(row) => row.word} caption="Recurring words" pageSize={15} /></Section>
            <Section title="By assistant"><DataTable columns={sourceColumns} rows={data.sources} getKey={(row) => row.source} caption="Prompts by assistant" /></Section>
          </>
        )}
      </ResourceView>
      <Callout tone="info">Nuxtron does not know how often these prompts are asked across the web. The numbers are your own log.</Callout>
    </Page>
  );
}
