"use client";

import { useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import { apiGet, apiSend } from "@/app/lib/platform-api";
import { Badge, Button, Callout, DataTable, EmptyState, Field, FieldSelect, FieldTextarea, IconButton, Kpi, KpiGrid, Modal, Page, PageHeader, Section, Tabs, type Column } from "../_ui/kit";
import { formatDateTime, truncate } from "../_ui/format";
import { ResourceView, useResource, useTenant } from "../_ui/use-resource";

type Mention = { id: number; platform: string; query: string; author_handle: string; text: string; sentiment: string; engagement_count: number; created_at: string };
type Keyword = { id: number; keyword: string; networks: string[]; alert_threshold: number; alert_on_crisis: boolean };
type Rule = { id: number; name: string; query?: string | null; platform?: string | null; min_engagement: number; negative_only: boolean };
type Summary = { totals: { mentions: number; alerts: number; open_alerts: number; rules: number }; sentiment_breakdown: Record<string, number>; crisis_level: string };
type Loaded = { summary: Summary; mentions: Mention[]; keywords: Keyword[]; rules: Rule[] };
type Tab = "mentions" | "keywords" | "rules";

const PLATFORMS = ["linkedin", "x", "instagram", "facebook", "reddit", "youtube", "news"];

export default function SocialListeningPage() {
  const tenant = useTenant();
  const resource = useResource<Loaded>(async (id) => {
    const [summary, mentions, keywords, rules] = await Promise.all([
      apiGet<Summary>("/social/listening/summary", id),
      apiGet<{ mentions?: Mention[] }>("/social/listening/mentions", id),
      apiGet<{ keywords?: Keyword[] }>("/social/listening/keywords", id),
      apiGet<{ rules?: Rule[] }>("/social/listening/rules", id),
    ]);
    return { summary, mentions: mentions.mentions ?? [], keywords: keywords.keywords ?? [], rules: rules.rules ?? [] };
  });

  const [tab, setTab] = useState<Tab>("mentions");
  const [modal, setModal] = useState<Tab | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [keyword, setKeyword] = useState("");
  const [ruleName, setRuleName] = useState("");
  const [ruleQuery, setRuleQuery] = useState("");
  const [platform, setPlatform] = useState(PLATFORMS[0]);
  const [query, setQuery] = useState("");
  const [author, setAuthor] = useState("");
  const [text, setText] = useState("");
  const [sentiment, setSentiment] = useState("neutral");

  async function run(action: () => Promise<unknown>, done?: () => void) {
    setBusy(true);
    setError(null);
    try {
      await action();
      done?.();
      await resource.reload();
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "That action failed.");
    } finally {
      setBusy(false);
    }
  }

  const mentionColumns: Column<Mention>[] = [
    { key: "text", header: "Mention", strong: true, render: (mention) => <span>{truncate(mention.text, 140)}<br /><span style={{ color: "var(--nx-muted)", fontWeight: 400 }}>@{mention.author_handle} · {mention.platform}</span></span> },
    { key: "query", header: "Matched", sortValue: (mention) => mention.query, render: (mention) => <Badge>{mention.query}</Badge> },
    { key: "sentiment", header: "Sentiment", sortValue: (mention) => mention.sentiment, render: (mention) => <Badge tone={mention.sentiment === "negative" ? "danger" : mention.sentiment === "positive" ? "success" : "neutral"}>{mention.sentiment}</Badge> },
    { key: "engagement", header: "Engagement", numeric: true, sortValue: (mention) => mention.engagement_count, render: (mention) => mention.engagement_count.toLocaleString() },
    { key: "when", header: "Logged", sortValue: (mention) => mention.created_at, render: (mention) => formatDateTime(mention.created_at) },
  ];
  const keywordColumns: Column<Keyword>[] = [
    { key: "keyword", header: "Keyword", strong: true, render: (item) => item.keyword },
    { key: "networks", header: "Networks", render: (item) => item.networks.join(", ") },
    { key: "threshold", header: "Alert at", numeric: true, render: (item) => item.alert_threshold.toLocaleString() },
    { key: "crisis", header: "Crisis alerts", render: (item) => (item.alert_on_crisis ? "On" : "Off") },
    { key: "actions", header: "", render: (item) => <IconButton label={`Remove ${item.keyword}`} variant="quiet" onClick={() => void run(() => apiSend(`/social/listening/keywords/${item.id}`, "DELETE", undefined, tenant))}><Trash2 size={15} aria-hidden="true" /></IconButton> },
  ];
  const ruleColumns: Column<Rule>[] = [
    { key: "name", header: "Rule", strong: true, render: (rule) => rule.name },
    { key: "query", header: "Matches", render: (rule) => rule.query || "Everything" },
    { key: "min", header: "Min. engagement", numeric: true, render: (rule) => rule.min_engagement.toLocaleString() },
    { key: "neg", header: "Negative only", render: (rule) => (rule.negative_only ? "Yes" : "No") },
  ];

  return (
    <Page>
      <PageHeader
        title="Social Listening"
        subtitle="Track the words that matter and log what people say. Mentions are recorded from your connected sources and from entries you add."
        actions={
          <Button variant="primary" icon={<Plus size={15} aria-hidden="true" />} onClick={() => { setModal(tab); setError(null); }}>
            {tab === "mentions" ? "Log a mention" : tab === "keywords" ? "Add keyword" : "Add rule"}
          </Button>
        }
        tabs={<Tabs items={[{ id: "mentions", label: "Mentions", count: resource.data?.mentions.length }, { id: "keywords", label: "Keywords", count: resource.data?.keywords.length }, { id: "rules", label: "Alert rules", count: resource.data?.rules.length }]} value={tab} onChange={(id) => setTab(id as Tab)} />}
      />
      <ResourceView resource={resource}>
        {(data) => (
          <>
            <KpiGrid>
              <Kpi label="Mentions" value={data.summary.totals.mentions} />
              <Kpi label="Open alerts" value={data.summary.totals.open_alerts} />
              <Kpi label="Positive" value={data.summary.sentiment_breakdown.positive ?? 0} />
              <Kpi label="Negative" value={data.summary.sentiment_breakdown.negative ?? 0} />
            </KpiGrid>
            {data.summary.crisis_level !== "normal" ? <Callout tone="danger" title={`Crisis level: ${data.summary.crisis_level}`}>Negative mentions are above your alert thresholds.</Callout> : null}
            <Section title={tab === "mentions" ? "Mentions" : tab === "keywords" ? "Tracked keywords" : "Alert rules"}>
              {tab === "mentions" ? (
                data.mentions.length === 0 ? <EmptyState title="No mentions yet" description="Log a mention you found, or connect a source that reports them." /> : <DataTable columns={mentionColumns} rows={data.mentions} getKey={(mention) => mention.id} caption="Mentions" pageSize={15} />
              ) : tab === "keywords" ? (
                data.keywords.length === 0 ? <EmptyState title="No keywords tracked" description="Add the brand names, products and topics you want to watch." /> : <DataTable columns={keywordColumns} rows={data.keywords} getKey={(item) => item.id} caption="Tracked keywords" />
              ) : data.rules.length === 0 ? (
                <EmptyState title="No alert rules" description="Create a rule to flag mentions that need attention." />
              ) : (
                <DataTable columns={ruleColumns} rows={data.rules} getKey={(rule) => rule.id} caption="Alert rules" />
              )}
            </Section>
          </>
        )}
      </ResourceView>

      <Modal
        open={modal !== null}
        onOpenChange={(open) => !open && setModal(null)}
        title={modal === "mentions" ? "Log a mention" : modal === "keywords" ? "Add keyword" : "Add alert rule"}
        footer={
          <>
            <Button onClick={() => setModal(null)} disabled={busy}>Cancel</Button>
            <Button
              variant="primary"
              loading={busy}
              onClick={() => {
                if (modal === "keywords") {
                  if (!keyword.trim()) return setError("Enter a keyword.");
                  void run(() => apiSend("/social/listening/keywords", "POST", { keyword: keyword.trim() }, tenant), () => { setModal(null); setKeyword(""); });
                } else if (modal === "rules") {
                  if (ruleName.trim().length < 2) return setError("Give the rule a name.");
                  void run(() => apiSend("/social/listening/rules", "POST", { name: ruleName.trim(), query: ruleQuery.trim() || null }, tenant), () => { setModal(null); setRuleName(""); setRuleQuery(""); });
                } else {
                  if (query.trim().length < 2 || !author.trim() || text.trim().length < 3) return setError("Add the keyword it matched, who said it, and what they said.");
                  void run(() => apiSend("/social/listening/ingest", "POST", { platform, query: query.trim(), author_handle: author.trim().replace(/^@/, ""), text: text.trim(), sentiment }, tenant), () => { setModal(null); setText(""); setAuthor(""); });
                }
              }}
            >
              Save
            </Button>
          </>
        }
      >
        <div style={{ display: "grid", gap: 14 }}>
          {error ? <Callout tone="danger">{error}</Callout> : null}
          {modal === "keywords" ? <Field label="Keyword" value={keyword} maxLength={200} onChange={(event) => setKeyword(event.target.value)} /> : null}
          {modal === "rules" ? (
            <>
              <Field label="Rule name" value={ruleName} maxLength={120} onChange={(event) => setRuleName(event.target.value)} />
              <Field label="Matches (optional)" value={ruleQuery} onChange={(event) => setRuleQuery(event.target.value)} hint="Leave empty to match every mention." />
            </>
          ) : null}
          {modal === "mentions" ? (
            <>
              <FieldSelect label="Where" value={platform} onChange={(event) => setPlatform(event.target.value)}>{PLATFORMS.map((item) => <option key={item} value={item}>{item}</option>)}</FieldSelect>
              <Field label="Keyword it matched" value={query} maxLength={120} onChange={(event) => setQuery(event.target.value)} />
              <Field label="Author handle" value={author} maxLength={120} onChange={(event) => setAuthor(event.target.value)} />
              <FieldTextarea label="What they said" rows={4} value={text} maxLength={4000} onChange={(event) => setText(event.target.value)} />
              <FieldSelect label="Sentiment" value={sentiment} onChange={(event) => setSentiment(event.target.value)}><option value="positive">Positive</option><option value="neutral">Neutral</option><option value="negative">Negative</option></FieldSelect>
            </>
          ) : null}
        </div>
      </Modal>
    </Page>
  );
}
