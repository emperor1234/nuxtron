"use client";

import { useMemo, useState } from "react";
import { apiGet, apiSend } from "@/app/lib/platform-api";
import { Badge, Button, Callout, Card, EmptyState, FieldTextarea, Page, PageHeader, StatusBadge, Tabs } from "../../../_ui/kit";
import { formatDateTime, truncate } from "../../../_ui/format";
import { ResourceView, useResource, useTenant } from "../../../_ui/use-resource";
import styles from "./inbox.module.css";

type Message = {
  id: number;
  network: string;
  source_type: string;
  author_handle: string;
  author_display_name?: string;
  text: string;
  sentiment?: string;
  priority_score?: number;
  suggested_replies?: string[];
  status: string;
  assigned_to?: string | null;
  replied?: boolean;
  read?: boolean;
  created_at: string;
};

type Filter = "open" | "mine" | "done";

export default function SocialInboxPage() {
  const tenant = useTenant();
  const resource = useResource<Message[]>(async (id) => (await apiGet<{ items?: Message[] }>("/social/inbox", id)).items ?? []);
  const [filter, setFilter] = useState<Filter>("open");
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [reply, setReply] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const messages = useMemo(() => resource.data ?? [], [resource.data]);
  const visible = useMemo(
    () =>
      messages
        .filter((message) => (filter === "done" ? message.status === "complete" || message.replied : filter === "mine" ? Boolean(message.assigned_to) && message.status !== "complete" : message.status !== "complete" && !message.replied))
        .sort((a, b) => (b.priority_score ?? 0) - (a.priority_score ?? 0) || b.created_at.localeCompare(a.created_at)),
    [messages, filter],
  );
  const selected = messages.find((message) => message.id === selectedId) ?? null;

  async function run(action: () => Promise<unknown>) {
    setBusy(true);
    setError(null);
    try {
      await action();
      await resource.reload();
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "That action failed.");
    } finally {
      setBusy(false);
    }
  }

  function open(message: Message) {
    setSelectedId(message.id);
    setReply("");
    setError(null);
    if (!message.read) void apiSend(`/social/inbox/${message.id}/read`, "PUT", {}, tenant).then(() => resource.reload()).catch(() => undefined);
  }

  return (
    <Page width="wide">
      <PageHeader
        title="Social Inbox"
        subtitle="Messages, comments and mentions from your connected accounts, ordered by priority."
        tabs={
          <Tabs
            items={[
              { id: "open", label: "Open", count: messages.filter((m) => m.status !== "complete" && !m.replied).length },
              { id: "mine", label: "Assigned" },
              { id: "done", label: "Done" },
            ]}
            value={filter}
            onChange={(id) => setFilter(id as Filter)}
          />
        }
      />
      <ResourceView
        resource={resource}
        isEmpty={(items) => items.length === 0}
        empty={<EmptyState title="Your inbox is empty" description="Messages appear here when a connected account receives them. Connect an account in Connected Accounts to start." />}
      >
        {() => (
          <div className={styles.layout}>
            <Card pad={false} className={styles.list}>
              {visible.length === 0 ? (
                <p className={styles.none}>Nothing in this view.</p>
              ) : (
                <ul role="list" className={styles.items}>
                  {visible.map((message) => (
                    <li key={message.id}>
                      <button type="button" className={`${styles.item} ${message.id === selectedId ? styles.active : ""}`} onClick={() => open(message)}>
                        <span className={styles.top}>
                          <strong>{message.author_display_name || message.author_handle}</strong>
                          {message.read ? null : <span className={styles.dot} aria-label="Unread" />}
                          <span className={styles.net}>{message.network}</span>
                        </span>
                        <span className={styles.snippet}>{truncate(message.text, 110)}</span>
                        <span className={styles.meta}>{message.source_type} · {formatDateTime(message.created_at)}</span>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </Card>
            <Card className={styles.detail}>
              {!selected ? (
                <EmptyState title="Select a message" description="Pick a message on the left to read it and reply." />
              ) : (
                <div className={styles.stack}>
                  <div className={styles.head}>
                    <div>
                      <h2 className={styles.name}>{selected.author_display_name || selected.author_handle}</h2>
                      <p className={styles.sub}>@{selected.author_handle} · {selected.network} · {selected.source_type}</p>
                    </div>
                    <div className={styles.badges}>
                      <StatusBadge status={selected.status} />
                      {selected.sentiment ? <Badge tone={selected.sentiment === "negative" ? "danger" : selected.sentiment === "positive" ? "success" : "neutral"}>{selected.sentiment}</Badge> : null}
                    </div>
                  </div>
                  <p className={styles.body}>{selected.text}</p>
                  {error ? <Callout tone="danger">{error}</Callout> : null}
                  {selected.replied ? (
                    <Callout tone="success">This message has been answered.</Callout>
                  ) : (
                    <>
                      {(selected.suggested_replies?.length ?? 0) > 0 ? (
                        <div>
                          <p className={styles.label}>Suggested replies</p>
                          <div className={styles.chips}>
                            {selected.suggested_replies?.map((suggestion) => (
                              <Button key={suggestion} size="sm" onClick={() => setReply(suggestion)}>
                                {truncate(suggestion, 60)}
                              </Button>
                            ))}
                          </div>
                        </div>
                      ) : null}
                      <FieldTextarea label="Your reply" rows={4} value={reply} maxLength={1000} onChange={(event) => setReply(event.target.value)} />
                      <div className={styles.actions}>
                        <Button variant="primary" loading={busy} disabled={reply.trim().length < 2} onClick={() => void run(() => apiSend(`/social/inbox/${selected.id}/respond`, "POST", { response_text: reply.trim() }, tenant)).then(() => setReply(""))}>
                          Send reply
                        </Button>
                        {!selected.assigned_to ? (
                          <Button disabled={busy} onClick={() => void run(() => apiSend(`/social/inbox/messages/${selected.id}/claim`, "POST", { agent_name: "Social Desk" }, tenant))}>
                            Assign to me
                          </Button>
                        ) : null}
                        <Button variant="quiet" disabled={busy} onClick={() => void run(() => apiSend(`/social/inbox/messages/${selected.id}/complete`, "POST", {}, tenant))}>
                          Mark done
                        </Button>
                      </div>
                    </>
                  )}
                </div>
              )}
            </Card>
          </div>
        )}
      </ResourceView>
    </Page>
  );
}
