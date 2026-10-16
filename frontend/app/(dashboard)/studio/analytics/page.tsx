"use client";

import { apiGet } from "@/app/lib/platform-api";
import { Callout, Card, EmptyState, KpiGrid, Kpi, Page, PageHeader, Section } from "../../_ui/kit";
import { formatNumber } from "../../_ui/format";
import { ResourceView, useResource } from "../../_ui/use-resource";

type Metrics = {
  content_pieces_generated: number;
  social_posts_scheduled: number;
  email_campaigns: number;
  crm_contacts: number;
  seo_analyses: number;
  ad_campaigns: number;
};

const LABELS: Array<[keyof Metrics, string, string]> = [
  ["content_pieces_generated", "Content generated", "Pieces written in this workspace"],
  ["social_posts_scheduled", "Posts planned", "Saved in the Social Studio planner"],
  ["email_campaigns", "Email campaigns", "Campaigns created"],
  ["crm_contacts", "CRM contacts", "Contacts stored"],
  ["seo_analyses", "SEO analyses", "Saved analysis runs"],
  ["ad_campaigns", "Ad jobs", "Ad generation jobs"],
];

export default function StudioAnalyticsPage() {
  const resource = useResource<Metrics>(async (tenant) => (await apiGet<{ metrics: Metrics }>("/analytics/metrics", tenant)).metrics, []);

  return (
    <Page width="wide">
      <PageHeader title="Workspace Activity" subtitle="A count of what your team has created in Nuxtron. These are record counts, not audience or revenue figures." />
      <ResourceView resource={resource} isEmpty={(data) => Object.values(data).every((value) => !value)} empty={
        <EmptyState title="No activity yet" description="Counts appear here after you generate content, plan posts or add contacts." />
      }>
        {(data) => (
          <Section title="Your workspace">
            <KpiGrid>
              {LABELS.map(([key, label, hint]) => <Kpi key={key} label={label} value={formatNumber(data[key])} hint={hint} />)}
            </KpiGrid>
          </Section>
        )}
      </ResourceView>
      <Card>
        <Callout tone="info" title="Looking for reach or engagement?">
          Audience and engagement figures need a connected social account or analytics source. Nuxtron does not estimate them.
        </Callout>
      </Card>
    </Page>
  );
}
