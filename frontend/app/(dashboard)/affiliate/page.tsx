"use client";

import { useState } from "react";
import { apiGet, apiSend } from "@/app/lib/platform-api";
import { Button, Callout, Card, DataTable, EmptyState, ErrorState, Kpi, KpiGrid, Page, PageHeader, Section, type Column } from "../_ui/kit";
import { CopyButton } from "../_ui/generator";
import { formatDateTime, formatNumber } from "../_ui/format";
import { ResourceView, useResource, useTenant } from "../_ui/use-resource";

type Overview = {
  referral_rewards: { referrer_credits: number; referred_credits: number };
  profile: { referral_code: string; successful_referrals: number; total_credits_earned: number; last_referral_at?: string | null };
  claims: Array<{ claimed_at?: string; referred_email?: string; credits?: number }>;
};

export default function AffiliatePage() {
  const tenant = useTenant();
  const resource = useResource<Overview>((id) => apiGet<Overview>("/engagement/referrals", id), []);
  const [failure, setFailure] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  async function ensureCode() {
    setBusy(true);
    setFailure(null);
    try {
      await apiSend("/engagement/referrals/generate-code", "POST", undefined, tenant);
      resource.reload();
    } catch (caught) {
      setFailure(caught);
    } finally {
      setBusy(false);
    }
  }

  const columns: Column<Overview["claims"][number]>[] = [
    { key: "who", header: "Referred", strong: true, render: (row) => row.referred_email || "—" },
    { key: "credits", header: "Credits", numeric: true, render: (row) => formatNumber(row.credits) },
    { key: "when", header: "Date", render: (row) => formatDateTime(row.claimed_at) },
  ];

  return (
    <Page width="wide">
      <PageHeader title="Referrals" subtitle="Share your code. You and the person you refer both earn credits." />
      {failure ? <ErrorState error={failure} title="That did not work" /> : null}
      <ResourceView resource={resource}>
        {(data) => (
          <>
            <Card>
              <div style={{ display: "grid", gap: 12 }}>
                <span style={{ fontSize: 13, color: "var(--nx-muted)" }}>Your referral code</span>
                <code style={{ fontSize: 24, fontWeight: 700 }}>{data.profile.referral_code}</code>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                  <CopyButton text={data.profile.referral_code} label="Copy code" />
                  <Button loading={busy} onClick={() => void ensureCode()}>Refresh</Button>
                </div>
              </div>
            </Card>
            <KpiGrid>
              <Kpi label="Successful referrals" value={formatNumber(data.profile.successful_referrals)} />
              <Kpi label="Credits earned" value={formatNumber(data.profile.total_credits_earned)} />
              <Kpi label="You earn per referral" value={formatNumber(data.referral_rewards.referrer_credits)} />
              <Kpi label="They earn" value={formatNumber(data.referral_rewards.referred_credits)} />
            </KpiGrid>
            <Section title="Referral history">
              {data.claims.length ? <DataTable columns={columns} rows={data.claims} getKey={(_, index) => index} caption="Referral history" pageSize={10} /> : <EmptyState title="No referrals yet" description="Referrals appear once someone signs up with your code." />}
            </Section>
          </>
        )}
      </ResourceView>
      <Callout tone="info">Credits are added when a referred workspace claims your code.</Callout>
    </Page>
  );
}
