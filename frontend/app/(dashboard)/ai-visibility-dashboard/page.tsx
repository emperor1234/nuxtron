"use client";

import { useState, type FormEvent } from "react";
import { Plus, Trash2 } from "lucide-react";
import { apiGet, apiSend } from "@/app/lib/platform-api";
import { Button, Callout, ConfirmModal, DataTable, Drawer, EmptyState, ErrorState, Field, FieldSelect, FormActions, Kpi, KpiGrid, Modal, Page, PageHeader, Section, Tabs, type Column } from "../_ui/kit";
import { CopyButton } from "../_ui/generator";
import { formatDateTime, formatNumber } from "../_ui/format";
import { ResourceView, useResource, useTenant } from "../_ui/use-resource";

type Site = { id: string; domain: string; display_name: string; cms_type: string; snippet_installed: boolean; ssr_enabled: boolean; ai_crawlers_detected_total: number; created_at: string };
type Dashboard = {
  window_hours: number;
  summary: { total_hits: number; ai_crawler_hits: number; blocked_hits: number; sites_registered: number; sites_with_snippet: number };
  top_crawlers: Array<{ crawler?: string; name?: string; hits?: number; count?: number }>;
  top_pages: Array<{ path?: string; url?: string; hits?: number; count?: number }>;
};

const CMS = ["custom", "wordpress", "shopify", "wix", "webflow", "next_js", "nuxt", "angular", "vue", "react", "gatsby", "hugo", "jekyll"];
const WINDOWS = [{ id: "24", label: "24 hours" }, { id: "168", label: "7 days" }, { id: "720", label: "30 days" }];

function Snippet({ site }: { site: Site }) {
  const sample = JSON.stringify({ site_id: site.id, crawler_name: "GPTBot", page_url: `https://${site.domain}/pricing`, user_agent: "<the request's User-Agent header>", status_code: 200, response_type: "live" }, null, 2);
  const command = `curl -X POST "$NUXTRON_API/ai-crawler/events" \\\n  -H "Authorization: Bearer $NUXTRON_TOKEN" -H "Content-Type: application/json" \\\n  -d '${sample.replace(/'/g, "")}'`;
  return (
    <div style={{ display: "grid", gap: 14 }}>
      <p style={{ margin: 0, fontSize: 14, lineHeight: 1.55 }}>AI crawlers do not run page scripts, so visits are read from your server. Forward one event per crawler request from your web server, CDN or log pipeline. Site ID: <code>{site.id}</code></p>
      <pre style={{ margin: 0, padding: 14, borderRadius: 8, background: "var(--nx-paper-2, #f3efe6)", overflowX: "auto", fontSize: 12.5 }}><code>{command}</code></pre>
      <div><CopyButton text={command} label="Copy example" /></div>
    </div>
  );
}

export default function AiVisibilityPage() {
  const tenant = useTenant();
  const [hours, setHours] = useState("168");
  const dashboard = useResource<Dashboard>((id) => apiGet<Dashboard>(`/ai-crawler/dashboard?window_hours=${hours}`, id), [hours]);
  const sites = useResource<Site[]>(async (id) => (await apiGet<{ sites: Site[] }>("/ai-crawler/sites", id)).sites, []);
  const [open, setOpen] = useState(false);
  const [domain, setDomain] = useState("");
  const [name, setName] = useState("");
  const [cms, setCms] = useState("custom");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [failure, setFailure] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const [selected, setSelected] = useState<Site | null>(null);
  const [removing, setRemoving] = useState<Site | null>(null);

  async function add(event: FormEvent) {
    event.preventDefault();
    const found: Record<string, string> = {};
    if (domain.trim().length < 3 || !domain.includes(".")) found.domain = "Enter a domain such as example.com.";
    if (!name.trim()) found.name = "Give the site a name.";
    setErrors(found);
    if (Object.keys(found).length) return;
    setBusy(true);
    setFailure(null);
    try {
      await apiSend("/ai-crawler/sites", "POST", { domain: domain.trim(), display_name: name.trim(), cms_type: cms }, tenant);
      setOpen(false);
      setDomain("");
      setName("");
      sites.reload();
      dashboard.reload();
    } catch (caught) {
      setFailure(caught);
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    if (!removing) return;
    try {
      await apiSend(`/ai-crawler/sites/${encodeURIComponent(removing.id)}`, "DELETE", undefined, tenant);
      sites.reload();
      dashboard.reload();
    } catch (caught) {
      setFailure(caught);
    }
    setRemoving(null);
  }

  const columns: Column<Site>[] = [
    { key: "site", header: "Site", strong: true, render: (row) => <span>{row.display_name}<br /><span style={{ color: "var(--nx-muted)", fontWeight: 400 }}>{row.domain}</span></span>, sortValue: (row) => row.domain },
    { key: "bots", header: "AI bot visits", numeric: true, render: (row) => formatNumber(row.ai_crawlers_detected_total), sortValue: (row) => row.ai_crawlers_detected_total },
    { key: "added", header: "Added", render: (row) => formatDateTime(row.created_at) },
    { key: "x", header: "", render: (row) => (
      <span style={{ display: "flex", gap: 6 }}>
        <Button size="sm" onClick={() => setSelected(row)}>Send events</Button>
        <Button size="sm" variant="ghost" icon={<Trash2 size={14} aria-hidden="true" />} aria-label={`Remove ${row.display_name}`} onClick={() => setRemoving(row)} />
      </span>
    ) },
  ];

  return (
    <Page width="wide">
      <PageHeader title="AI Visibility" subtitle="See which AI crawlers visit your sites. Counts come from the crawler events your server sends." actions={<Button variant="primary" icon={<Plus size={15} aria-hidden="true" />} onClick={() => setOpen(true)}>Add a site</Button>} tabs={<Tabs items={WINDOWS} value={hours} onChange={setHours} label="Period" />} />
      <ResourceView resource={dashboard}>
        {(data) => (
          <KpiGrid>
            <Kpi label="AI crawler hits" value={formatNumber(data.summary.ai_crawler_hits)} />
            <Kpi label="All hits recorded" value={formatNumber(data.summary.total_hits)} />
            <Kpi label="Blocked" value={formatNumber(data.summary.blocked_hits)} />
            <Kpi label="Sites" value={formatNumber(data.summary.sites_registered)} />
          </KpiGrid>
        )}
      </ResourceView>
      {failure && !open ? <ErrorState error={failure} title="That did not work" /> : null}
      <Section title="Your sites">
        <ResourceView resource={sites} isEmpty={(rows) => rows.length === 0} empty={<EmptyState title="No sites yet" description="Add a site, then send its crawler events." action={<Button variant="primary" onClick={() => setOpen(true)}>Add a site</Button>} />}>
          {(rows) => <DataTable columns={columns} rows={rows} getKey={(row) => row.id} caption="Sites" />}
        </ResourceView>
      </Section>
      <Callout tone="info">A site shows no visits until your server starts sending events.</Callout>
      <Modal open={open} onOpenChange={setOpen} title="Add a site">
        <form onSubmit={add} noValidate style={{ display: "grid", gap: 16 }}>
          <Field label="Domain" value={domain} error={errors.domain} maxLength={120} placeholder="example.com" onChange={(event) => setDomain(event.target.value)} />
          <Field label="Name" value={name} error={errors.name} maxLength={80} onChange={(event) => setName(event.target.value)} />
          <FieldSelect label="Platform" value={cms} onChange={(event) => setCms(event.target.value)}>{CMS.map((item) => <option key={item} value={item}>{item}</option>)}</FieldSelect>
          {failure ? <ErrorState error={failure} title="Not saved" /> : null}
          <FormActions><Button onClick={() => setOpen(false)}>Cancel</Button><Button type="submit" variant="primary" loading={busy}>Add site</Button></FormActions>
        </form>
      </Modal>
      <Drawer open={Boolean(selected)} onOpenChange={(next) => !next && setSelected(null)} title={selected?.display_name ?? ""} description={selected?.domain}>{selected ? <Snippet site={selected} /> : null}</Drawer>
      <ConfirmModal open={Boolean(removing)} onOpenChange={(next) => !next && setRemoving(null)} title="Remove this site?" description={`${removing?.domain ?? ""} and its recorded visits are deleted.`} confirmLabel="Remove" onConfirm={() => void remove()} />
    </Page>
  );
}
