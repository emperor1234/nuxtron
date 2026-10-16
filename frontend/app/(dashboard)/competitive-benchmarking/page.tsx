"use client";

import { useState, type FormEvent } from "react";
import { Plus, Trash2 } from "lucide-react";
import { apiGet, apiSend } from "@/app/lib/platform-api";
import { Badge, Button, Callout, ConfirmModal, DataTable, EmptyState, ErrorState, Field, FieldSelect, FormActions, Modal, Page, PageHeader, Section, type Column } from "../_ui/kit";
import { formatNumber, formatPercent } from "../_ui/format";
import { ResourceView, useResource, useTenant } from "../_ui/use-resource";

type Snapshot = { followers: number; engagement_rate: number; estimated_mentions: number; snapshot_date: string; network: string };
type Competitor = { profile: { id: number; name: string; network: string; handle: string; last_snapshot_date?: string }; latest_snapshot?: Snapshot | null; vs_own?: { followers_delta: number; engagement_rate_delta: number; ahead: boolean } };
type Report = { own_brand: Snapshot | null; competitors: Competitor[] };
type Share = { breakdown: Array<{ brand: string; estimated_mentions: number; share_pct: number }> };

const NETWORKS = ["instagram", "facebook", "linkedin", "twitter", "tiktok", "youtube"];

function Numbers({ title, endpoint, network, onDone, open, onOpenChange }: { title: string; endpoint: string; network?: string; onDone: () => void; open: boolean; onOpenChange: (open: boolean) => void }) {
  const tenant = useTenant();
  const [net, setNet] = useState(network ?? "instagram");
  const [followers, setFollowers] = useState("");
  const [rate, setRate] = useState("");
  const [mentions, setMentions] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [failure, setFailure] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  async function save(event: FormEvent) {
    event.preventDefault();
    const found: Record<string, string> = {};
    if (!/^\d+$/.test(followers)) found.followers = "Enter a whole number.";
    if (rate === "" || Number.isNaN(Number(rate)) || Number(rate) < 0 || Number(rate) > 100) found.rate = "Enter a percentage from 0 to 100.";
    if (mentions !== "" && !/^\d+$/.test(mentions)) found.mentions = "Enter a whole number.";
    setErrors(found);
    if (Object.keys(found).length) return;
    setBusy(true);
    setFailure(null);
    try {
      await apiSend(endpoint, "POST", { network: net, followers: Number(followers), engagement_rate: Number(rate), estimated_mentions: Number(mentions || 0) }, tenant);
      onOpenChange(false);
      setFollowers("");
      setRate("");
      setMentions("");
      onDone();
    } catch (caught) {
      setFailure(caught);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal open={open} onOpenChange={onOpenChange} title={title} description="Enter the figures you read from the public profile today.">
      <form onSubmit={save} noValidate style={{ display: "grid", gap: 16 }}>
        <FieldSelect label="Network" value={net} onChange={(event) => setNet(event.target.value)}>{NETWORKS.map((item) => <option key={item} value={item}>{item}</option>)}</FieldSelect>
        <Field label="Followers" inputMode="numeric" value={followers} error={errors.followers} onChange={(event) => setFollowers(event.target.value)} />
        <Field label="Engagement rate (%)" inputMode="decimal" value={rate} error={errors.rate} onChange={(event) => setRate(event.target.value)} />
        <Field label="Mentions this month" inputMode="numeric" value={mentions} error={errors.mentions} onChange={(event) => setMentions(event.target.value)} />
        {failure ? <ErrorState error={failure} title="Not saved" /> : null}
        <FormActions><Button onClick={() => onOpenChange(false)}>Cancel</Button><Button type="submit" variant="primary" loading={busy}>Save</Button></FormActions>
      </form>
    </Modal>
  );
}

export default function CompetitiveBenchmarkingPage() {
  const tenant = useTenant();
  const report = useResource<Report>((id) => apiGet<Report>("/competitive/report", id), []);
  const share = useResource<Share>((id) => apiGet<Share>("/competitive/share-of-voice", id), []);
  const [addOpen, setAddOpen] = useState(false);
  const [ownOpen, setOwnOpen] = useState(false);
  const [snap, setSnap] = useState<Competitor | null>(null);
  const [removing, setRemoving] = useState<Competitor | null>(null);
  const [name, setName] = useState("");
  const [network, setNetwork] = useState("instagram");
  const [handle, setHandle] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [failure, setFailure] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  function reload() {
    report.reload();
    share.reload();
  }

  async function add(event: FormEvent) {
    event.preventDefault();
    const found: Record<string, string> = {};
    if (!name.trim()) found.name = "Name the competitor.";
    if (!handle.trim()) found.handle = "Enter their handle.";
    setErrors(found);
    if (Object.keys(found).length) return;
    setBusy(true);
    setFailure(null);
    try {
      await apiSend("/competitive/profiles", "POST", { name: name.trim(), network, handle: handle.trim() }, tenant);
      setAddOpen(false);
      setName("");
      setHandle("");
      reload();
    } catch (caught) {
      setFailure(caught);
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    if (!removing) return;
    try {
      await apiSend(`/competitive/profiles/${removing.profile.id}`, "DELETE", undefined, tenant);
      reload();
    } catch (caught) {
      setFailure(caught);
    }
    setRemoving(null);
  }

  const columns: Column<Competitor>[] = [
    { key: "name", header: "Competitor", strong: true, render: (row) => <span>{row.profile.name}<br /><span style={{ color: "var(--nx-muted)", fontWeight: 400 }}>{row.profile.network} · @{row.profile.handle}</span></span>, sortValue: (row) => row.profile.name },
    { key: "followers", header: "Followers", numeric: true, render: (row) => (row.latest_snapshot ? formatNumber(row.latest_snapshot.followers) : "—"), sortValue: (row) => row.latest_snapshot?.followers ?? 0 },
    { key: "rate", header: "Engagement", numeric: true, render: (row) => (row.latest_snapshot ? formatPercent(row.latest_snapshot.engagement_rate) : "—"), sortValue: (row) => row.latest_snapshot?.engagement_rate ?? 0 },
    { key: "vs", header: "Versus you", render: (row) => (row.vs_own ? <Badge tone={row.vs_own.ahead ? "danger" : "success"}>{row.vs_own.ahead ? "Ahead of you" : "Behind you"}</Badge> : "—") },
    { key: "date", header: "Updated", render: (row) => row.profile.last_snapshot_date ?? "Never" },
    { key: "x", header: "", render: (row) => (
      <span style={{ display: "flex", gap: 6 }}>
        <Button size="sm" onClick={() => setSnap(row)}>Update figures</Button>
        <Button size="sm" variant="ghost" icon={<Trash2 size={14} aria-hidden="true" />} aria-label={`Remove ${row.profile.name}`} onClick={() => setRemoving(row)} />
      </span>
    ) },
  ];

  return (
    <Page width="wide">
      <PageHeader title="Competitor Benchmarking" subtitle="Compare your social numbers with competitors. You enter the figures; Nuxtron keeps the history and works out the gaps." actions={<><Button onClick={() => setOwnOpen(true)}>Record your numbers</Button><Button variant="primary" icon={<Plus size={15} aria-hidden="true" />} onClick={() => setAddOpen(true)}>Add competitor</Button></>} />
      {failure && !addOpen ? <ErrorState error={failure} title="That did not work" /> : null}
      <ResourceView resource={report} isEmpty={(data) => data.competitors.length === 0} empty={<EmptyState title="No competitors tracked" description="Add a competitor, then enter their public follower and engagement figures." action={<Button variant="primary" onClick={() => setAddOpen(true)}>Add competitor</Button>} />}>
        {(data) => (
          <>
            {!data.own_brand ? <Callout tone="info">Record your own numbers to see how each competitor compares.</Callout> : null}
            <DataTable columns={columns} rows={data.competitors} getKey={(row) => row.profile.id} caption="Competitors" />
          </>
        )}
      </ResourceView>
      <ResourceView resource={share} isEmpty={(data) => data.breakdown.length === 0} empty={null}>
        {(data) => (
          <Section title="Share of voice" description="Based on the mention counts you entered.">
            <DataTable columns={[
              { key: "brand", header: "Brand", strong: true, render: (row: Share["breakdown"][number]) => row.brand },
              { key: "m", header: "Mentions", numeric: true, render: (row: Share["breakdown"][number]) => formatNumber(row.estimated_mentions) },
              { key: "s", header: "Share", numeric: true, render: (row: Share["breakdown"][number]) => formatPercent(row.share_pct), sortValue: (row: Share["breakdown"][number]) => row.share_pct },
            ]} rows={data.breakdown} getKey={(row) => row.brand} caption="Share of voice" />
          </Section>
        )}
      </ResourceView>
      <Modal open={addOpen} onOpenChange={setAddOpen} title="Add competitor">
        <form onSubmit={add} noValidate style={{ display: "grid", gap: 16 }}>
          <Field label="Name" value={name} error={errors.name} maxLength={80} onChange={(event) => setName(event.target.value)} />
          <FieldSelect label="Network" value={network} onChange={(event) => setNetwork(event.target.value)}>{NETWORKS.map((item) => <option key={item} value={item}>{item}</option>)}</FieldSelect>
          <Field label="Handle" value={handle} error={errors.handle} maxLength={80} onChange={(event) => setHandle(event.target.value)} />
          {failure ? <ErrorState error={failure} title="Not saved" /> : null}
          <FormActions><Button onClick={() => setAddOpen(false)}>Cancel</Button><Button type="submit" variant="primary" loading={busy}>Add</Button></FormActions>
        </form>
      </Modal>
      <Numbers title="Record your numbers" endpoint="/competitive/own-profile" open={ownOpen} onOpenChange={setOwnOpen} onDone={reload} />
      {snap ? <Numbers key={snap.profile.id} title={`Update ${snap.profile.name}`} endpoint={`/competitive/profiles/${snap.profile.id}/snapshots`} network={snap.profile.network} open onOpenChange={(next) => !next && setSnap(null)} onDone={reload} /> : null}
      <ConfirmModal open={Boolean(removing)} onOpenChange={(next) => !next && setRemoving(null)} title="Remove this competitor?" description={`${removing?.profile.name ?? ""} and its saved figures are deleted.`} confirmLabel="Remove" onConfirm={() => void remove()} />
    </Page>
  );
}
