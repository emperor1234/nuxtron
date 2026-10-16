"use client";

import { useMemo } from "react";
import { apiGet } from "@/app/lib/platform-api";
import { ButtonLink, Card, EmptyState, Kpi, KpiGrid, Page, PageHeader, StatusBadge } from "../../../_ui/kit";
import { formatDate, truncate } from "../../../_ui/format";
import { ResourceView, useResource } from "../../../_ui/use-resource";
import { platformLabel, postText, type QueuePost } from "../_lib/social";
import styles from "./queue.module.css";

type ApprovalSummary = { id: number; status: string };

type Loaded = { posts: QueuePost[]; pendingApprovals: number };

function dayLabel(iso: string | null | undefined): string {
  if (!iso) return "No date";
  return formatDate(iso);
}

export default function ContentQueuePage() {
  const resource = useResource<Loaded>(async (tenant) => {
    const [queue, approvals] = await Promise.all([
      apiGet<{ queue?: QueuePost[] }>("/social/queue?status=all&limit=200", tenant),
      apiGet<{ requests?: ApprovalSummary[] }>("/content/approval/requests?approval_status=pending", tenant),
    ]);
    return { posts: queue.queue ?? [], pendingApprovals: (approvals.requests ?? []).length };
  });

  const grouped = useMemo(() => {
    const upcoming = (resource.data?.posts ?? [])
      .filter((post) => post.status !== "published" && post.status !== "rejected")
      .sort((a, b) => String(a.publish_at ?? "").localeCompare(String(b.publish_at ?? "")));
    const groups = new Map<string, QueuePost[]>();
    for (const post of upcoming) {
      const key = dayLabel(post.publish_at);
      groups.set(key, [...(groups.get(key) ?? []), post]);
    }
    return { upcoming, groups: [...groups.entries()] };
  }, [resource.data]);

  const drafts = (resource.data?.posts ?? []).filter((post) => post.status === "draft").length;

  return (
    <Page>
      <PageHeader
        title="Content Queue"
        subtitle="What is planned next, grouped by day. Nuxtron keeps the plan; it does not publish for you."
        actions={<ButtonLink href="/studio/social-studio/posts" variant="primary">Plan a post</ButtonLink>}
      />
      <ResourceView resource={resource}>
        {(data) => (
          <>
            <KpiGrid>
              <Kpi label="Planned" value={grouped.upcoming.length} />
              <Kpi label="Drafts" value={drafts} />
              <Kpi label="Awaiting approval" value={data.pendingApprovals} hint="Review in Content Approvals" />
            </KpiGrid>
            {grouped.groups.length === 0 ? (
              <EmptyState
                title="Nothing is planned"
                description="Plan a post, import a batch, or turn an idea into a post to build your queue."
                action={<ButtonLink href="/studio/social-studio/bulk-schedule">Import a batch</ButtonLink>}
              />
            ) : (
              grouped.groups.map(([day, posts]) => (
                <section key={day} aria-label={day} className={styles.day}>
                  <h2 className={styles.dayTitle}>{day}</h2>
                  <Card pad={false}>
                    <ul className={styles.list}>
                      {posts.map((post) => (
                        <li key={post.id} className={styles.row}>
                          <span className={styles.time}>
                            {post.publish_at
                              ? new Date(post.publish_at).toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" })
                              : "—"}
                          </span>
                          <span className={styles.text}>{truncate(postText(post) || "(no text)", 160)}</span>
                          <span className={styles.meta}>{platformLabel(post.platform)}</span>
                          <StatusBadge status={post.status} />
                        </li>
                      ))}
                    </ul>
                  </Card>
                </section>
              ))
            )}
          </>
        )}
      </ResourceView>
    </Page>
  );
}
