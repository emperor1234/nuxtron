"use client";

import { useMemo, useState } from "react";
import { Plus, Trash2, CalendarClock } from "lucide-react";
import { apiGet, apiSend } from "@/app/lib/platform-api";
import {
  Button,
  Callout,
  ConfirmModal,
  DataTable,
  EmptyState,
  Field,
  FieldSelect,
  FieldTextarea,
  IconButton,
  Modal,
  Page,
  PageHeader,
  ButtonLink,
  SearchField,
  StatusBadge,
  Tabs,
  Toolbar,
  type Column,
} from "../../../_ui/kit";
import { formatDateTime, fromLocalInputValue, toLocalInputValue, truncate } from "../../../_ui/format";
import { ResourceView, useResource, useTenant } from "../../../_ui/use-resource";
import { platformLabel, postText, SCHEDULE_PLATFORMS, type QueuePost } from "../_lib/social";

type Filter = "all" | "scheduled" | "draft" | "pending_approval" | "published";

const FILTERS: Array<{ id: Filter; label: string }> = [
  { id: "all", label: "All" },
  { id: "scheduled", label: "Planned" },
  { id: "draft", label: "Drafts" },
  { id: "pending_approval", label: "Pending approval" },
  { id: "published", label: "Published" },
];

type Loaded = { posts: QueuePost[] };

function defaultPublishAt(): string {
  const next = new Date(Date.now() + 60 * 60 * 1000);
  next.setMinutes(0, 0, 0);
  return toLocalInputValue(next);
}

export default function PostSchedulerPage() {
  const tenant = useTenant();
  const resource = useResource<Loaded>(async (id) => {
    const queue = await apiGet<{ queue?: QueuePost[] }>("/social/queue?status=all&limit=200", id);
    return { posts: queue.queue ?? [] };
  });

  const [filter, setFilter] = useState<Filter>("all");
  const [query, setQuery] = useState("");
  const [composeOpen, setComposeOpen] = useState(false);
  const [platform, setPlatform] = useState<string>(SCHEDULE_PLATFORMS[0].value);
  const [text, setText] = useState("");
  const [publishAt, setPublishAt] = useState(defaultPublishAt);
  const [media, setMedia] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const [moving, setMoving] = useState<QueuePost | null>(null);
  const [moveTo, setMoveTo] = useState("");
  const [deleting, setDeleting] = useState<QueuePost | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const rows = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return (resource.data?.posts ?? []).filter((post) => {
      if (filter !== "all" && post.status !== filter) return false;
      return !needle || postText(post).toLowerCase().includes(needle) || post.platform.includes(needle);
    });
  }, [resource.data, filter, query]);

  const counts = useMemo(() => {
    const result: Record<string, number> = {};
    for (const post of resource.data?.posts ?? []) result[post.status] = (result[post.status] ?? 0) + 1;
    return result;
  }, [resource.data]);

  async function submit() {
    setFormError(null);
    const iso = fromLocalInputValue(publishAt);
    const body = text.trim();
    if (body.length < 3) return setFormError("Write at least 3 characters.");
    if (body.length > 2200) return setFormError("Posts can be at most 2,200 characters.");
    if (!iso) return setFormError("Choose when you plan to post.");
    if (new Date(iso).getTime() < Date.now() - 60_000) return setFormError("Choose a time in the future.");
    const mediaUrls = media.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
    setSaving(true);
    try {
      await apiSend("/social/schedule", "POST", { platform, text: body, publish_at: iso, media_urls: mediaUrls }, tenant);
      setComposeOpen(false);
      setText("");
      setMedia("");
      setPublishAt(defaultPublishAt());
      await resource.reload();
    } catch (error) {
      setFormError(error instanceof Error ? error.message : "The post could not be added.");
    } finally {
      setSaving(false);
    }
  }

  async function run(action: () => Promise<unknown>, done: () => void) {
    setBusy(true);
    setActionError(null);
    try {
      await action();
      done();
      await resource.reload();
    } catch (error) {
      setActionError(error instanceof Error ? error.message : "That action failed.");
    } finally {
      setBusy(false);
    }
  }

  const columns: Column<QueuePost>[] = [
    {
      key: "text",
      header: "Post",
      strong: true,
      sortValue: (post) => postText(post),
      render: (post) => (
        <span>
          {truncate(postText(post) || "(no text)", 120)}
          {post.media_urls?.length ? <span style={{ color: "var(--nx-muted)" }}> · {post.media_urls.length} media</span> : null}
        </span>
      ),
    },
    { key: "platform", header: "Platform", sortValue: (post) => post.platform, render: (post) => platformLabel(post.platform) },
    { key: "when", header: "Planned for", sortValue: (post) => post.publish_at ?? "", render: (post) => formatDateTime(post.publish_at) },
    { key: "status", header: "Status", sortValue: (post) => post.status, render: (post) => <StatusBadge status={post.status} /> },
    {
      key: "actions",
      header: "Actions",
      render: (post) =>
        post.status === "published" ? null : (
          <span style={{ display: "inline-flex", gap: 6 }}>
            <IconButton
              label="Reschedule"
              onClick={() => {
                setMoving(post);
                setMoveTo(post.publish_at ? toLocalInputValue(new Date(post.publish_at)) : defaultPublishAt());
                setActionError(null);
              }}
            >
              <CalendarClock size={15} aria-hidden="true" />
            </IconButton>
            <IconButton
              label="Delete"
              variant="quiet"
              onClick={() => {
                setDeleting(post);
                setActionError(null);
              }}
            >
              <Trash2 size={15} aria-hidden="true" />
            </IconButton>
          </span>
        ),
    },
  ];


  return (
    <Page>
      <PageHeader
        title="Post Planner"
        subtitle="Plan posts and keep them in one list. Nuxtron stores your plan; it does not publish to your accounts for you."
        actions={
          <Button variant="primary" icon={<Plus size={15} aria-hidden="true" />} onClick={() => setComposeOpen(true)}>
            New post
          </Button>
        }
        tabs={
          <Tabs
            items={FILTERS.map((item) => ({ ...item, count: item.id === "all" ? resource.data?.posts.length : counts[item.id] ?? 0 }))}
            value={filter}
            onChange={(id) => setFilter(id as Filter)}
            label="Post status"
          />
        }
      />

      {actionError ? <Callout tone="danger">{actionError}</Callout> : null}

      <Toolbar>
        <SearchField value={query} onChange={setQuery} placeholder="Search posts" label="Search posts" />
      </Toolbar>

      <ResourceView resource={resource}>
        {() =>
          rows.length === 0 ? (
            <EmptyState
              title={(resource.data?.posts.length ?? 0) === 0 ? "No posts yet" : "No posts match"}
              description={
                (resource.data?.posts.length ?? 0) === 0
                  ? "Plan your first post to see it here and on the calendar."
                  : "Try a different status or search."
              }
              action={
                (resource.data?.posts.length ?? 0) === 0 ? (
                  <Button variant="primary" onClick={() => setComposeOpen(true)}>
                    New post
                  </Button>
                ) : (
                  <ButtonLink href="/studio/social-studio/calendar">Open the calendar</ButtonLink>
                )
              }
            />
          ) : (
            <DataTable columns={columns} rows={rows} getKey={(post) => post.id} caption="Social posts" pageSize={15} />
          )
        }
      </ResourceView>

      <Modal
        open={composeOpen}
        onOpenChange={(open) => {
          setComposeOpen(open);
          if (!open) setFormError(null);
        }}
        title="Plan a post"
        description="Add the post to your plan for the date and time you will post it."
        footer={
          <>
            <Button onClick={() => setComposeOpen(false)} disabled={saving}>
              Cancel
            </Button>
            <Button variant="primary" loading={saving} onClick={() => void submit()}>
              Add to plan
            </Button>
          </>
        }
      >
        <div style={{ display: "grid", gap: 16 }}>
          {formError ? <Callout tone="danger">{formError}</Callout> : null}
          <FieldSelect label="Platform" value={platform} onChange={(event) => setPlatform(event.target.value)}>
            {SCHEDULE_PLATFORMS.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </FieldSelect>
          <FieldTextarea
            label="Post text"
            rows={6}
            value={text}
            maxLength={2200}
            onChange={(event) => setText(event.target.value)}
            hint={`${text.length.toLocaleString()} / 2,200`}
          />
          <Field label="Planned for" type="datetime-local" value={publishAt} onChange={(event) => setPublishAt(event.target.value)} />
          <FieldTextarea
            label="Media URLs"
            rows={3}
            value={media}
            onChange={(event) => setMedia(event.target.value)}
            placeholder="One image or video URL per line (optional)"
          />
        </div>
      </Modal>

      <Modal
        open={Boolean(moving)}
        onOpenChange={(open) => !open && setMoving(null)}
        title="Reschedule post"
        description={moving ? truncate(postText(moving), 100) : undefined}
        footer={
          <>
            <Button onClick={() => setMoving(null)} disabled={busy}>
              Cancel
            </Button>
            <Button
              variant="primary"
              loading={busy}
              onClick={() => {
                const iso = fromLocalInputValue(moveTo);
                if (!moving || !iso) return setActionError("Choose a valid time.");
                void run(
                  () => apiSend(`/social/scheduled/${moving.id}/move`, "PATCH", { new_publish_at: iso }, tenant),
                  () => setMoving(null),
                );
              }}
            >
              Reschedule
            </Button>
          </>
        }
      >
        {actionError ? <Callout tone="danger">{actionError}</Callout> : null}
        <Field label="New publish time" type="datetime-local" value={moveTo} onChange={(event) => setMoveTo(event.target.value)} />
      </Modal>

      <ConfirmModal
        open={Boolean(deleting)}
        onOpenChange={(open) => !open && setDeleting(null)}
        title="Delete this post?"
        description={deleting ? `“${truncate(postText(deleting), 80)}” will be removed from the schedule. This cannot be undone.` : ""}
        pending={busy}
        error={actionError}
        onConfirm={() => deleting && void run(() => apiSend(`/social/scheduled/${deleting.id}`, "DELETE", undefined, tenant), () => setDeleting(null))}
      />
    </Page>
  );
}
