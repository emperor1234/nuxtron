"use client";

import { useState } from "react";
import { Link2, Unplug } from "lucide-react";
import { apiGet, apiSend } from "@/app/lib/platform-api";
import { Badge, Button, Callout, Card, CardTitle, ConfirmModal, DataTable, EmptyState, Grid, Page, PageHeader, Section, StatusBadge, type Column } from "../../../_ui/kit";
import { formatDate, formatNumber } from "../../../_ui/format";
import { ResourceView, useResource, useTenant } from "../../../_ui/use-resource";
import type { SocialAccount } from "../_lib/social";

type Provider = { network: string; label: string; supported_formats?: string[] };
type OAuthStart = { mode?: string; configured?: boolean; authorization_url?: string; provider_label?: string };
type Loaded = { accounts: SocialAccount[]; providers: Provider[] };

export default function ConnectedAccountsPage() {
  const tenant = useTenant();
  const resource = useResource<Loaded>(async (id) => {
    const [accounts, catalog] = await Promise.all([
      apiGet<{ accounts?: SocialAccount[] }>("/social/accounts", id),
      apiGet<{ providers?: Provider[] }>("/social/accounts/catalog", id),
    ]);
    return { accounts: accounts.accounts ?? [], providers: catalog.providers ?? [] };
  });

  const [connecting, setConnecting] = useState<string | null>(null);
  const [notice, setNotice] = useState<{ tone: "warning" | "danger"; text: string } | null>(null);
  const [removing, setRemoving] = useState<SocialAccount | null>(null);
  const [busy, setBusy] = useState(false);
  const [removeError, setRemoveError] = useState<string | null>(null);

  async function connect(provider: Provider) {
    setConnecting(provider.network);
    setNotice(null);
    try {
      const start = await apiSend<OAuthStart>(`/social/oauth/${provider.network}/start`, "POST", {}, tenant);
      if (!start.configured || !start.authorization_url) {
        setNotice({
          tone: "warning",
          text: `${provider.label} sign-in is not configured for this deployment, so an account cannot be connected yet. An administrator needs to add the ${provider.label} app credentials.`,
        });
        return;
      }
      window.location.assign(start.authorization_url);
    } catch (error) {
      setNotice({ tone: "danger", text: error instanceof Error ? error.message : `Could not start the ${provider.label} sign-in.` });
    } finally {
      setConnecting(null);
    }
  }

  async function disconnect() {
    if (!removing) return;
    setBusy(true);
    setRemoveError(null);
    try {
      await apiSend(`/social/accounts/${removing.id}`, "DELETE", undefined, tenant);
      setRemoving(null);
      await resource.reload();
    } catch (error) {
      setRemoveError(error instanceof Error ? error.message : "The account could not be disconnected.");
    } finally {
      setBusy(false);
    }
  }

  const columns: Column<SocialAccount>[] = [
    { key: "name", header: "Account", strong: true, sortValue: (account) => account.account_name, render: (account) => <span>{account.account_name}<br /><span style={{ color: "var(--nx-muted)", fontWeight: 400 }}>@{account.handle}</span></span> },
    { key: "network", header: "Network", sortValue: (account) => account.network_label, render: (account) => account.network_label },
    { key: "status", header: "Connection", render: (account) => <StatusBadge status={account.oauth_status} /> },
    { key: "followers", header: "Followers", numeric: true, render: (account) => (account.followers ? formatNumber(account.followers) : "—") },
    { key: "since", header: "Connected", sortValue: (account) => account.connected_at ?? "", render: (account) => formatDate(account.connected_at) },
    {
      key: "actions",
      header: "",
      render: (account) => (
        <Button size="sm" variant="quiet" icon={<Unplug size={14} aria-hidden="true" />} onClick={() => { setRemoving(account); setRemoveError(null); }}>
          Disconnect
        </Button>
      ),
    },
  ];

  return (
    <Page>
      <PageHeader title="Connected Accounts" subtitle="Connect the social accounts Nuxtron works with. You sign in on the network itself; Nuxtron never sees your password." />
      {notice ? <Callout tone={notice.tone}>{notice.text}</Callout> : null}
      <ResourceView resource={resource}>
        {(data) => (
          <>
            <Section title="Your accounts">
              {data.accounts.length === 0 ? (
                <EmptyState title="No accounts connected" description="Choose a network below to sign in and connect an account." icon={<Link2 size={22} aria-hidden="true" />} />
              ) : (
                <DataTable columns={columns} rows={data.accounts} getKey={(account) => account.id} caption="Connected social accounts" />
              )}
            </Section>
            <Section title="Connect a network" description="Audience figures appear only after the network reports them.">
              <Grid cols={4}>
                {data.providers.map((provider) => {
                  const count = data.accounts.filter((account) => account.network === provider.network).length;
                  return (
                    <Card key={provider.network}>
                      <CardTitle sub={count ? `${count} connected` : undefined}>{provider.label}</CardTitle>
                      <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 12 }}>
                        {(provider.supported_formats ?? []).slice(0, 4).map((format) => <Badge key={format}>{format}</Badge>)}
                      </div>
                      <Button size="sm" variant="primary" loading={connecting === provider.network} onClick={() => void connect(provider)}>
                        Connect
                      </Button>
                    </Card>
                  );
                })}
              </Grid>
            </Section>
          </>
        )}
      </ResourceView>
      <ConfirmModal
        open={Boolean(removing)}
        onOpenChange={(open) => !open && setRemoving(null)}
        title="Disconnect this account?"
        description={removing ? `${removing.account_name} will be disconnected. Your planned posts stay in your plan.` : ""}
        confirmLabel="Disconnect"
        pending={busy}
        error={removeError}
        onConfirm={() => void disconnect()}
      />
    </Page>
  );
}
