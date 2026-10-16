"use client";

import { useState } from "react";
import { Plus } from "lucide-react";
import { apiGet, apiSend } from "@/app/lib/platform-api";
import { Button, Callout, Card, CardTitle, DataTable, EmptyState, Field, FormGrid, Kpi, KpiGrid, Modal, Page, PageHeader, Section, type Column } from "../_ui/kit";
import { formatCurrency, formatDate, formatNumber, formatPercent } from "../_ui/format";
import { ResourceView, useResource, useTenant } from "../_ui/use-resource";

type Summary = {
  window_days: number;
  currency_codes: string[];
  totals: { revenue: number | null; spend: number | null; net_profit: number | null; roas: number | null; roi_pct: number | null; conversions: number; touchpoints: number; spend_entries: number };
  channels: Array<{ channel: string; spend?: number | null; revenue?: number | null }>;
};
type SpendEntry = { id: number; channel: string; campaign: string; amount: number; currency: string; spent_at?: string | null; notes?: string };
type Loaded = { summary: Summary; spend: SpendEntry[] };
type Calculation = Record<string, unknown>;

export default function SocialMediaRoiPage() {
  const tenant = useTenant();
  const resource = useResource<Loaded>(async (id) => {
    const [summary, spend] = await Promise.all([
      apiGet<Summary>("/analytics/social-roi/summary?window_days=90", id),
      apiGet<{ items?: SpendEntry[] }>("/analytics/social-roi/spend?limit=100", id),
    ]);
    return { summary, spend: spend.items ?? [] };
  });

  const [open, setOpen] = useState(false);
  const [channel, setChannel] = useState("");
  const [campaign, setCampaign] = useState("");
  const [amount, setAmount] = useState("");
  const [currency, setCurrency] = useState("USD");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [revenue, setRevenue] = useState("");
  const [paid, setPaid] = useState("");
  const [team, setTeam] = useState("");
  const [tools, setTools] = useState("");
  const [agency, setAgency] = useState("");
  const [result, setResult] = useState<Calculation | null>(null);
  const [calcBusy, setCalcBusy] = useState(false);
  const [calcError, setCalcError] = useState<string | null>(null);

  async function saveSpend() {
    const value = Number(amount);
    if (!channel.trim() || !Number.isFinite(value) || value < 0) return setError("Add a channel and a valid amount.");
    setBusy(true);
    setError(null);
    try {
      await apiSend("/analytics/social-roi/spend", "POST", { channel: channel.trim(), campaign: campaign.trim(), amount: value, currency: currency.trim().toUpperCase() }, tenant);
      setOpen(false);
      setChannel("");
      setCampaign("");
      setAmount("");
      await resource.reload();
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "The spend could not be saved.");
    } finally {
      setBusy(false);
    }
  }

  async function calculate() {
    const revenueValue = Number(revenue);
    if (!Number.isFinite(revenueValue) || revenueValue < 0) return setCalcError("Enter the revenue you attribute to social, as a number.");
    setCalcBusy(true);
    setCalcError(null);
    try {
      const body = { attributed_revenue: revenueValue, paid_social_spend: Number(paid) || 0, team_cost: Number(team) || 0, tools_cost: Number(tools) || 0, agency_cost: Number(agency) || 0 };
      setResult(await apiSend<Calculation>("/analytics/social-roi/calculator", "POST", body, tenant));
    } catch (failure) {
      setCalcError(failure instanceof Error ? failure.message : "The calculation failed.");
    } finally {
      setCalcBusy(false);
    }
  }

  const columns: Column<SpendEntry>[] = [
    { key: "channel", header: "Channel", strong: true, sortValue: (entry) => entry.channel, render: (entry) => entry.channel },
    { key: "campaign", header: "Campaign", render: (entry) => entry.campaign || "—" },
    { key: "amount", header: "Amount", numeric: true, sortValue: (entry) => entry.amount, render: (entry) => formatCurrency(entry.amount, entry.currency) },
    { key: "date", header: "Date", sortValue: (entry) => entry.spent_at ?? "", render: (entry) => formatDate(entry.spent_at) },
  ];

  return (
    <Page>
      <PageHeader
        title="Social Media ROI"
        subtitle="Record what you spend on social and see return against the revenue you attribute to it. Figures come only from entries and tracked conversions you provide."
        actions={<Button variant="primary" icon={<Plus size={15} aria-hidden="true" />} onClick={() => { setOpen(true); setError(null); }}>Record spend</Button>}
      />
      <ResourceView resource={resource}>
        {(data) => {
          const totals = data.summary.totals;
          return (
            <>
              <KpiGrid>
                <Kpi label="Spend (90 days)" value={totals.spend === null ? "—" : formatNumber(totals.spend)} hint={data.summary.currency_codes.join(", ") || "No spend recorded"} />
                <Kpi label="Attributed revenue" value={totals.revenue === null ? "—" : formatNumber(totals.revenue)} />
                <Kpi label="ROAS" value={totals.roas === null ? "—" : totals.roas.toFixed(2)} />
                <Kpi label="ROI" value={formatPercent(totals.roi_pct)} />
              </KpiGrid>
              <Section title="Spend you recorded">
                {data.spend.length === 0 ? <EmptyState title="No spend recorded" description="Record what you spend on each channel to calculate return." action={<Button variant="primary" onClick={() => setOpen(true)}>Record spend</Button>} /> : <DataTable columns={columns} rows={data.spend} getKey={(entry) => entry.id} caption="Recorded spend" pageSize={10} />}
              </Section>
              <Card>
                <CardTitle sub="A what-if calculator. It uses only the numbers you type below.">ROI calculator</CardTitle>
                <div style={{ display: "grid", gap: 14 }}>
                  {calcError ? <Callout tone="danger">{calcError}</Callout> : null}
                  <FormGrid>
                    <Field label="Revenue attributed to social" inputMode="decimal" value={revenue} onChange={(event) => setRevenue(event.target.value)} />
                    <Field label="Paid social spend" inputMode="decimal" value={paid} onChange={(event) => setPaid(event.target.value)} />
                    <Field label="Team cost" inputMode="decimal" value={team} onChange={(event) => setTeam(event.target.value)} />
                    <Field label="Tools cost" inputMode="decimal" value={tools} onChange={(event) => setTools(event.target.value)} />
                    <Field label="Agency cost" inputMode="decimal" value={agency} onChange={(event) => setAgency(event.target.value)} />
                  </FormGrid>
                  <div><Button variant="primary" loading={calcBusy} onClick={() => void calculate()}>Calculate</Button></div>
                  {result ? (
                    <KpiGrid>
                      {Object.entries(result)
                        .filter(([, value]) => typeof value === "number")
                        .map(([key, value]) => <Kpi key={key} label={key.replace(/_/g, " ")} value={(value as number).toLocaleString(undefined, { maximumFractionDigits: 2 })} />)}
                    </KpiGrid>
                  ) : null}
                </div>
              </Card>
            </>
          );
        }}
      </ResourceView>
      <Modal
        open={open}
        onOpenChange={setOpen}
        title="Record spend"
        footer={<><Button onClick={() => setOpen(false)} disabled={busy}>Cancel</Button><Button variant="primary" loading={busy} onClick={() => void saveSpend()}>Save</Button></>}
      >
        <div style={{ display: "grid", gap: 14 }}>
          {error ? <Callout tone="danger">{error}</Callout> : null}
          <Field label="Channel" value={channel} maxLength={80} placeholder="e.g. LinkedIn ads" onChange={(event) => setChannel(event.target.value)} />
          <Field label="Campaign" value={campaign} maxLength={160} onChange={(event) => setCampaign(event.target.value)} />
          <FormGrid>
            <Field label="Amount" inputMode="decimal" value={amount} onChange={(event) => setAmount(event.target.value)} />
            <Field label="Currency" value={currency} maxLength={12} onChange={(event) => setCurrency(event.target.value)} />
          </FormGrid>
        </div>
      </Modal>
    </Page>
  );
}
