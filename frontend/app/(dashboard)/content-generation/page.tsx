"use client";

import { useState, type FormEvent } from "react";
import { Sparkles } from "lucide-react";
import { apiGet, apiSend } from "@/app/lib/platform-api";
import { Badge, Button, Callout, Card, DataTable, EmptyState, ErrorState, Field, FieldSelect, Page, PageHeader, Section, Skeleton, Split, Switch, Tabs, type Column } from "../_ui/kit";
import { formatDateTime, truncate } from "../_ui/format";
import { CopyButton, OutputBlock } from "../_ui/generator";
import { useResource, useTenant } from "../_ui/use-resource";

const CHANNELS = ["linkedin", "x", "instagram", "facebook", "blog", "tiktok", "youtube", "threads", "snapchat", "pinterest", "reddit"];
const TONES = ["professional", "casual", "bold", "friendly"];

type Generated = {
  generation_id?: string;
  channel: string;
  tone: string;
  headline: string;
  body: string;
  hashtags?: string[];
  seo?: { meta_title?: string; meta_description?: string; focus_keyword?: string };
  provider_used?: string;
  model_used?: string;
};

type LibraryItem = { generation_id?: string; id?: string | number; topic?: string; channel?: string; headline?: string; body?: string; created_at?: string };

export default function ContentGeneratorPage() {
  const tenant = useTenant();
  const [tab, setTab] = useState<"create" | "library">("create");
  const [topic, setTopic] = useState("");
  const [audience, setAudience] = useState("");
  const [channel, setChannel] = useState("linkedin");
  const [tone, setTone] = useState("professional");
  const [seo, setSeo] = useState(true);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<unknown>(null);
  const [result, setResult] = useState<Generated | null>(null);

  const library = useResource<LibraryItem[]>(async (id) => (await apiGet<{ items?: LibraryItem[] }>("/content/library", id)).items ?? [], [tab]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    const found: Record<string, string> = {};
    if (topic.trim().length < 3) found.topic = "Describe the topic in at least 3 characters.";
    if (audience.trim().length < 3) found.audience = "Say who this is for (at least 3 characters).";
    setErrors(found);
    if (Object.keys(found).length) return;
    setBusy(true);
    setFailure(null);
    setResult(null);
    try {
      setResult(await apiSend<Generated>("/content/generate", "POST", { topic: topic.trim(), audience: audience.trim(), channel, tone, include_seo: seo }, tenant));
    } catch (error) {
      setFailure(error);
    } finally {
      setBusy(false);
    }
  }

  const columns: Column<LibraryItem>[] = [
    { key: "headline", header: "Content", strong: true, render: (item) => <span>{item.headline || item.topic || "Untitled"}<br /><span style={{ color: "var(--nx-muted)", fontWeight: 400 }}>{truncate(item.body ?? "", 110)}</span></span> },
    { key: "channel", header: "Channel", render: (item) => (item.channel ? <Badge>{item.channel}</Badge> : "—") },
    { key: "when", header: "Created", sortValue: (item) => item.created_at ?? "", render: (item) => formatDateTime(item.created_at) },
  ];

  return (
    <Page width="wide">
      <PageHeader
        title="Content Generator"
        subtitle="Write copy for a channel from a topic and an audience. Output comes from the AI model connected to your workspace."
        tabs={<Tabs items={[{ id: "create", label: "Create" }, { id: "library", label: "Library", count: library.data?.length }]} value={tab} onChange={(id) => setTab(id as "create" | "library")} />}
      />
      {tab === "create" ? (
        <Split>
          <Card>
            <form onSubmit={submit} noValidate aria-label="Content details" style={{ display: "grid", gap: 16 }}>
              <Field label="Topic" value={topic} error={errors.topic} maxLength={180} placeholder="e.g. Launching our trail running range" onChange={(event) => setTopic(event.target.value)} />
              <Field label="Audience" value={audience} error={errors.audience} maxLength={120} placeholder="e.g. first-time trail runners" onChange={(event) => setAudience(event.target.value)} />
              <FieldSelect label="Channel" value={channel} onChange={(event) => setChannel(event.target.value)}>
                {CHANNELS.map((item) => <option key={item} value={item}>{item.charAt(0).toUpperCase() + item.slice(1)}</option>)}
              </FieldSelect>
              <FieldSelect label="Tone" value={tone} onChange={(event) => setTone(event.target.value)}>
                {TONES.map((item) => <option key={item} value={item}>{item.charAt(0).toUpperCase() + item.slice(1)}</option>)}
              </FieldSelect>
              <Switch label="Include SEO title and description" checked={seo} onChange={setSeo} />
              <Button type="submit" variant="primary" loading={busy} icon={<Sparkles size={15} aria-hidden="true" />}>{busy ? "Writing…" : "Generate"}</Button>
            </form>
          </Card>
          <div aria-live="polite">
            {busy ? (
              <div style={{ display: "grid", gap: 12 }} role="status"><Skeleton height={64} /><Skeleton height={200} /></div>
            ) : failure ? (
              <ErrorState error={failure} title="Nothing was generated" />
            ) : result ? (
              <Card>
                <div style={{ display: "grid", gap: 20 }}>
                  <OutputBlock title="Headline" text={result.headline} />
                  <OutputBlock title="Body" text={result.body} />
                  {result.hashtags?.length ? <OutputBlock title="Hashtags" text={result.hashtags.join(" ")}><div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>{result.hashtags.map((tag) => <Badge key={tag} tone="brand">{tag}</Badge>)}</div></OutputBlock> : null}
                  {result.seo?.meta_title ? <OutputBlock title="SEO" text={`${result.seo.meta_title}\n${result.seo.meta_description ?? ""}`} /> : null}
                  <p style={{ margin: 0, fontSize: 12.5, color: "var(--nx-muted)" }}>Written by {result.provider_used ?? "the connected model"}{result.model_used ? ` (${result.model_used})` : ""}. Review before publishing.</p>
                  <div><CopyButton text={`${result.headline}\n\n${result.body}\n\n${(result.hashtags ?? []).join(" ")}`} label="Copy everything" /></div>
                </div>
              </Card>
            ) : (
              <EmptyState title="Your draft will appear here" description="Fill in the topic and audience, then generate." />
            )}
          </div>
        </Split>
      ) : (
        <Section title="Saved generations" description="Content you generated earlier in this workspace.">
          {library.status === "error" && library.data === null ? <ErrorState error={library.error} onRetry={() => void library.reload()} /> : library.data && library.data.length > 0 ? (
            <DataTable columns={columns} rows={library.data} getKey={(item, index) => item.generation_id ?? item.id ?? index} caption="Content library" pageSize={15} />
          ) : (
            <EmptyState title="Nothing saved yet" description="Generated content appears here." />
          )}
        </Section>
      )}
      <Callout tone="info">Generated text is a starting point. Check facts and claims before you publish it.</Callout>
    </Page>
  );
}
