"use client";

import { useState } from "react";
import { apiGet } from "@/app/lib/platform-api";
import { Badge, DataTable, Drawer, EmptyState, Page, PageHeader, type Column } from "../../_ui/kit";
import { formatDateTime } from "../../_ui/format";
import { ResourceView, useResource } from "../../_ui/use-resource";
import { ResultView } from "../_tool/result-view";

type Analysis = { id: string; module: string; created_at?: string; payload: Record<string, unknown>; result: Record<string, unknown> };

const label = (value: string) => value.replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase());
const subject = (row: Analysis) => String(row.payload.url ?? row.payload.domain ?? row.payload.topic ?? row.payload.goal ?? row.payload.focus_keyword ?? "—");

export default function SeoHistoryPage() {
  const resource = useResource<Analysis[]>(async (tenant) => (await apiGet<{ analyses: Analysis[] }>("/seo-platform/analyses?limit=100", tenant)).analyses, []);
  const [selected, setSelected] = useState<Analysis | null>(null);
  const columns: Column<Analysis>[] = [
    { key: "module", header: "Tool", strong: true, render: (row) => <Badge>{label(row.module)}</Badge>, sortValue: (row) => row.module },
    { key: "subject", header: "Input", render: (row) => subject(row) },
    { key: "when", header: "Run", render: (row) => formatDateTime(row.created_at ?? (row.result.created_at as string | undefined)), sortValue: (row) => row.created_at ?? "" },
  ];
  return (
    <Page width="wide">
      <PageHeader title="Saved Analyses" subtitle="Every SEO tool run you saved, newest first." />
      <ResourceView resource={resource} isEmpty={(rows) => rows.length === 0} empty={<EmptyState title="Nothing saved yet" description="Results appear here after you run an SEO tool." />}>
        {(rows) => <DataTable columns={columns} rows={rows} getKey={(row) => row.id} onRowClick={setSelected} caption="Saved analyses" pageSize={20} />}
      </ResourceView>
      <Drawer open={Boolean(selected)} onOpenChange={(next) => !next && setSelected(null)} title={selected ? label(selected.module) : ""} description={selected ? subject(selected) : undefined}>
        {selected ? <ResultView result={selected.result as never} /> : null}
      </Drawer>
    </Page>
  );
}
