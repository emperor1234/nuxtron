"use client";

import { useState, type FormEvent } from "react";
import { apiGet, apiSend } from "@/app/lib/platform-api";
import { Button, Card, DataTable, EmptyState, ErrorState, Field, FieldSelect, FormActions, Page, PageHeader, Section, type Column } from "../../../_ui/kit";
import { formatNumber, formatPercent } from "../../../_ui/format";
import { ResourceView, useResource, useTenant } from "../../../_ui/use-resource";

type Keyword = { keyword: string; impressions: number; engagement: number; platforms: string[]; engagement_rate: number; weight: number };

const PLATFORMS = ["", "linkedin", "x", "instagram", "facebook", "tiktok", "youtube"];

export default function KeywordTrackerPage() {
  const tenant = useTenant();
  const resource = useResource<Keyword[]>(async (id) => (await apiGet<{ keywords: Keyword[] }>("/analytics/keywords/top", id)).keywords, []);
  const [keyword, setKeyword] = useState("");
  const [impressions, setImpressions] = useState("");
  const [engagement, setEngagement] = useState("");
  const [platform, setPlatform] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [failure, setFailure] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  async function track(event: FormEvent) {
    event.preventDefault();
    const found: Record<string, string> = {};
    if (!keyword.trim()) found.keyword = "Enter a keyword.";
    for (const [key, value] of [["impressions", impressions], ["engagement", engagement]] as const) {
      if (value && (!/^\d+$/.test(value))) found[key] = "Use a whole number.";
    }
    setErrors(found);
    if (Object.keys(found).length) return;
    setBusy(true);
    setFailure(null);
    try {
      await apiSend("/analytics/keywords/track", "POST", { keyword: keyword.trim(), impressions: Number(impressions || 0), engagement: Number(engagement || 0), platform: platform || undefined }, tenant);
      setKeyword("");
      setImpressions("");
      setEngagement("");
      resource.reload();
    } catch (caught) {
      setFailure(caught);
    } finally {
      setBusy(false);
    }
  }

  const columns: Column<Keyword>[] = [
    { key: "keyword", header: "Keyword", strong: true, render: (row) => row.keyword, sortValue: (row) => row.keyword },
    { key: "impressions", header: "Impressions", numeric: true, render: (row) => formatNumber(row.impressions), sortValue: (row) => row.impressions },
    { key: "engagement", header: "Engagements", numeric: true, render: (row) => formatNumber(row.engagement), sortValue: (row) => row.engagement },
    { key: "rate", header: "Rate", numeric: true, render: (row) => formatPercent(row.engagement_rate * 100), sortValue: (row) => row.engagement_rate },
    { key: "platforms", header: "Platforms", render: (row) => row.platforms.join(", ") || "—" },
  ];

  return (
    <Page width="wide">
      <PageHeader title="Keyword Tracker" subtitle="Record how the words in your posts perform. The cloud sizes each word by the impressions you log." />
      <Card>
        <form onSubmit={track} noValidate aria-label="Log a keyword" style={{ display: "grid", gap: 16 }}>
          <div style={{ display: "grid", gap: 16, gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))" }}>
            <Field label="Keyword" value={keyword} error={errors.keyword} maxLength={60} onChange={(event) => setKeyword(event.target.value)} />
            <Field label="Impressions" inputMode="numeric" value={impressions} error={errors.impressions} onChange={(event) => setImpressions(event.target.value)} />
            <Field label="Engagements" inputMode="numeric" value={engagement} error={errors.engagement} onChange={(event) => setEngagement(event.target.value)} />
            <FieldSelect label="Platform" value={platform} onChange={(event) => setPlatform(event.target.value)}>{PLATFORMS.map((item) => <option key={item} value={item}>{item || "Any"}</option>)}</FieldSelect>
          </div>
          {failure ? <ErrorState error={failure} title="Not saved" /> : null}
          <FormActions><Button type="submit" variant="primary" loading={busy}>Log keyword</Button></FormActions>
        </form>
      </Card>
      <ResourceView resource={resource} isEmpty={(rows) => rows.length === 0} empty={<EmptyState title="Nothing logged yet" description="Log a keyword with its impressions and engagements to start the cloud." />}>
        {(rows) => (
          <>
            <Section title="Word cloud">
              <Card>
                <div role="img" aria-label={`Word cloud of ${rows.length} keywords`} style={{ display: "flex", flexWrap: "wrap", gap: "6px 16px", alignItems: "baseline", justifyContent: "center", padding: 12 }}>
                  {rows.map((row) => <span key={row.keyword} style={{ fontSize: 14 + Math.round(row.weight / 4), fontWeight: 700, color: "var(--nx-blue, #2563c9)" }}>{row.keyword}</span>)}
                </div>
              </Card>
            </Section>
            <Section title="Details"><DataTable columns={columns} rows={rows} getKey={(row) => row.keyword} caption="Tracked keywords" pageSize={15} /></Section>
          </>
        )}
      </ResourceView>
    </Page>
  );
}
