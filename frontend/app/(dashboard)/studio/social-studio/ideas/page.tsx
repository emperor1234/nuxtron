"use client";

import { useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import { apiGet, apiSend } from "@/app/lib/platform-api";
import {
  Badge,
  Button,
  Callout,
  Card,
  CardTitle,
  ConfirmModal,
  DataTable,
  EmptyState,
  Field,
  FieldSelect,
  FieldTextarea,
  Grid,
  IconButton,
  Modal,
  Page,
  PageHeader,
  StatusBadge,
  Tabs,
  type Column,
} from "../../../_ui/kit";
import { formatDate, fromLocalInputValue, toLocalInputValue, truncate } from "../../../_ui/format";
import { ResourceView, useResource, useTenant } from "../../../_ui/use-resource";
import { SCHEDULE_PLATFORMS } from "../_lib/social";

type Idea = { id: number; title: string; body: string; source: string; tags: string[]; status: string; created_at: string };
type HashtagGroup = { id: number; name: string; hashtags: string[]; description?: string };
type Template = { id: string; name: string; content_type: string; body: string; networks: string[] };
type Loaded = { ideas: Idea[]; groups: HashtagGroup[]; templates: Template[] };
type Tab = "ideas" | "hashtags" | "templates";

const splitList = (text: string) =>
  text
    .split(/\r?\n|,/)
    .map((item) => item.trim())
    .filter(Boolean);

export default function IdeasPage() {
  const tenant = useTenant();
  const resource = useResource<Loaded>(async (id) => {
    const [ideas, groups, templates] = await Promise.all([
      apiGet<{ items?: Idea[] }>("/social/ideas", id),
      apiGet<{ hashtag_groups?: HashtagGroup[] }>("/social/hashtag-groups", id),
      apiGet<{ templates?: Template[] }>("/social/templates", id),
    ]);
    return { ideas: ideas.items ?? [], groups: groups.hashtag_groups ?? [], templates: templates.templates ?? [] };
  });

  const [tab, setTab] = useState<Tab>("ideas");
  const [ideaOpen, setIdeaOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [tags, setTags] = useState("");
  const [planning, setPlanning] = useState<Idea | null>(null);
  const [network, setNetwork] = useState<string>(SCHEDULE_PLATFORMS[0].value);
  const [planAt, setPlanAt] = useState("");
  const [groupOpen, setGroupOpen] = useState(false);
  const [groupName, setGroupName] = useState("");
  const [groupTags, setGroupTags] = useState("");
  const [deleting, setDeleting] = useState<HashtagGroup | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run(action: () => Promise<unknown>, done: () => void) {
    setBusy(true);
    setError(null);
    try {
      await action();
      done();
      await resource.reload();
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "That action failed.");
    } finally {
      setBusy(false);
    }
  }

  const ideaColumns: Column<Idea>[] = [
    { key: "title", header: "Idea", strong: true, sortValue: (idea) => idea.title, render: (idea) => <span>{idea.title}<br /><span style={{ color: "var(--nx-muted)", fontWeight: 400 }}>{truncate(idea.body, 110)}</span></span> },
    { key: "tags", header: "Tags", render: (idea) => idea.tags.map((tag) => <Badge key={tag}>{tag}</Badge>) },
    { key: "status", header: "Status", sortValue: (idea) => idea.status, render: (idea) => <StatusBadge status={idea.status} /> },
    { key: "created", header: "Added", sortValue: (idea) => idea.created_at, render: (idea) => formatDate(idea.created_at) },
    {
      key: "actions",
      header: "",
      render: (idea) => (
        <Button
          size="sm"
          onClick={() => {
            setPlanning(idea);
            setPlanAt(toLocalInputValue(new Date(Date.now() + 24 * 3600_000)));
            setError(null);
          }}
        >
          Plan it
        </Button>
      ),
    },
  ];

  return (
    <Page>
      <PageHeader
        title="Ideas & Drafts"
        subtitle="Keep ideas, reusable hashtag groups and templates together, then turn an idea into a planned post."
        actions={
          tab === "hashtags" ? (
            <Button variant="primary" icon={<Plus size={15} aria-hidden="true" />} onClick={() => setGroupOpen(true)}>New hashtag group</Button>
          ) : (
            <Button variant="primary" icon={<Plus size={15} aria-hidden="true" />} onClick={() => setIdeaOpen(true)}>New idea</Button>
          )
        }
        tabs={
          <Tabs
            items={[
              { id: "ideas", label: "Ideas", count: resource.data?.ideas.length },
              { id: "hashtags", label: "Hashtag groups", count: resource.data?.groups.length },
              { id: "templates", label: "Templates", count: resource.data?.templates.length },
            ]}
            value={tab}
            onChange={(id) => setTab(id as Tab)}
          />
        }
      />
      {error && !ideaOpen && !groupOpen && !planning && !deleting ? <Callout tone="danger">{error}</Callout> : null}

      <ResourceView resource={resource}>
        {(data) =>
          tab === "ideas" ? (
            data.ideas.length === 0 ? (
              <EmptyState title="No ideas yet" description="Capture an idea now and plan it when you are ready." action={<Button variant="primary" onClick={() => setIdeaOpen(true)}>New idea</Button>} />
            ) : (
              <DataTable columns={ideaColumns} rows={data.ideas} getKey={(idea) => idea.id} caption="Ideas" pageSize={15} />
            )
          ) : tab === "hashtags" ? (
            data.groups.length === 0 ? (
              <EmptyState title="No hashtag groups" description="Save sets of hashtags you use together." action={<Button variant="primary" onClick={() => setGroupOpen(true)}>New hashtag group</Button>} />
            ) : (
              <Grid cols={3}>
                {data.groups.map((group) => (
                  <Card key={group.id}>
                    <CardTitle
                      sub={group.description || undefined}
                      actions={
                        <IconButton label={`Delete ${group.name}`} variant="quiet" onClick={() => { setDeleting(group); setError(null); }}>
                          <Trash2 size={15} aria-hidden="true" />
                        </IconButton>
                      }
                    >
                      {group.name}
                    </CardTitle>
                    <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>{group.hashtags.map((tag) => <Badge key={tag} tone="brand">{tag}</Badge>)}</div>
                  </Card>
                ))}
              </Grid>
            )
          ) : (
            <Grid cols={3}>
              {data.templates.map((template) => (
                <Card key={template.id}>
                  <CardTitle sub={template.networks.join(", ")}>{template.name}</CardTitle>
                  <p style={{ margin: "0 0 12px", fontSize: 13.5, whiteSpace: "pre-wrap", color: "var(--nx-ink-2)" }}>{truncate(template.body, 220)}</p>
                  <Button size="sm" onClick={() => { setTitle(template.name); setBody(template.body); setTags(""); setIdeaOpen(true); setError(null); }}>
                    Start an idea from this
                  </Button>
                </Card>
              ))}
            </Grid>
          )
        }
      </ResourceView>

      <Modal
        open={ideaOpen}
        onOpenChange={setIdeaOpen}
        title="New idea"
        footer={
          <>
            <Button onClick={() => setIdeaOpen(false)} disabled={busy}>Cancel</Button>
            <Button
              variant="primary"
              loading={busy}
              onClick={() => {
                if (title.trim().length < 2 || body.trim().length < 2) return setError("Add a title and some text.");
                void run(
                  () => apiSend("/social/ideas", "POST", { title: title.trim(), body: body.trim(), source: "manual", tags: splitList(tags) }, tenant),
                  () => { setIdeaOpen(false); setTitle(""); setBody(""); setTags(""); setTab("ideas"); },
                );
              }}
            >
              Save idea
            </Button>
          </>
        }
      >
        <div style={{ display: "grid", gap: 14 }}>
          {error ? <Callout tone="danger">{error}</Callout> : null}
          <Field label="Title" value={title} maxLength={180} onChange={(event) => setTitle(event.target.value)} />
          <FieldTextarea label="Text" rows={6} value={body} maxLength={4000} onChange={(event) => setBody(event.target.value)} />
          <Field label="Tags" value={tags} onChange={(event) => setTags(event.target.value)} hint="Separate with commas." />
        </div>
      </Modal>

      <Modal
        open={Boolean(planning)}
        onOpenChange={(open) => !open && setPlanning(null)}
        title="Plan this idea"
        description={planning?.title}
        footer={
          <>
            <Button onClick={() => setPlanning(null)} disabled={busy}>Cancel</Button>
            <Button
              variant="primary"
              loading={busy}
              onClick={() => {
                if (!planning) return;
                const iso = fromLocalInputValue(planAt);
                void run(
                  () => apiSend(`/social/ideas/${planning.id}/queue`, "POST", { network, publish_at: iso }, tenant),
                  () => setPlanning(null),
                );
              }}
            >
              Add to plan
            </Button>
          </>
        }
      >
        <div style={{ display: "grid", gap: 14 }}>
          {error ? <Callout tone="danger">{error}</Callout> : null}
          <FieldSelect label="Platform" value={network} onChange={(event) => setNetwork(event.target.value)}>
            {SCHEDULE_PLATFORMS.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
          </FieldSelect>
          <Field label="Planned for" type="datetime-local" value={planAt} onChange={(event) => setPlanAt(event.target.value)} />
        </div>
      </Modal>

      <Modal
        open={groupOpen}
        onOpenChange={setGroupOpen}
        title="New hashtag group"
        footer={
          <>
            <Button onClick={() => setGroupOpen(false)} disabled={busy}>Cancel</Button>
            <Button
              variant="primary"
              loading={busy}
              onClick={() => {
                const hashtags = splitList(groupTags).map((tag) => (tag.startsWith("#") ? tag : `#${tag}`));
                if (!groupName.trim() || hashtags.length === 0) return setError("Add a name and at least one hashtag.");
                void run(
                  () => apiSend("/social/hashtag-groups", "POST", { name: groupName.trim(), hashtags }, tenant),
                  () => { setGroupOpen(false); setGroupName(""); setGroupTags(""); },
                );
              }}
            >
              Save group
            </Button>
          </>
        }
      >
        <div style={{ display: "grid", gap: 14 }}>
          {error ? <Callout tone="danger">{error}</Callout> : null}
          <Field label="Name" value={groupName} maxLength={100} onChange={(event) => setGroupName(event.target.value)} />
          <FieldTextarea label="Hashtags" rows={4} value={groupTags} onChange={(event) => setGroupTags(event.target.value)} hint="One per line or separated by commas." />
        </div>
      </Modal>

      <ConfirmModal
        open={Boolean(deleting)}
        onOpenChange={(open) => !open && setDeleting(null)}
        title="Delete this hashtag group?"
        description={deleting ? `“${deleting.name}” will be removed.` : ""}
        pending={busy}
        error={error}
        onConfirm={() => deleting && void run(() => apiSend(`/social/hashtag-groups/${deleting.id}`, "DELETE", undefined, tenant), () => setDeleting(null))}
      />
    </Page>
  );
}
