"use client";

import { useState, type FormEvent } from "react";
import { Plus } from "lucide-react";
import { apiGet, apiSend } from "@/app/lib/platform-api";
import { Badge, Button, DataTable, EmptyState, ErrorState, Field, FormActions, Modal, Page, PageHeader, type Column } from "../../../_ui/kit";
import { ResourceView, useResource, useTenant } from "../../../_ui/use-resource";

type Node = { brand_key: string; brand_name: string; parent_brand_key?: string | null; region?: string | null; industry?: string | null };

export default function BrandHierarchyPage() {
  const tenant = useTenant();
  const resource = useResource<Node[]>(async (id) => (await apiGet<{ brands: Node[] }>("/brand-hierarchy", id)).brands, []);
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [parent, setParent] = useState("");
  const [region, setRegion] = useState("");
  const [industry, setIndustry] = useState("");
  const [error, setError] = useState("");
  const [failure, setFailure] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  async function create(event: FormEvent) {
    event.preventDefault();
    if (name.trim().length < 2) return setError("Name the brand.");
    setError("");
    setBusy(true);
    setFailure(null);
    try {
      await apiSend("/brand-hierarchy", "POST", { child_brand_name: name.trim(), parent_brand_key: parent.trim() || undefined, region: region.trim() || undefined, industry: industry.trim() || undefined }, tenant);
      setOpen(false);
      setName("");
      setParent("");
      setRegion("");
      setIndustry("");
      resource.reload();
    } catch (caught) {
      setFailure(caught);
    } finally {
      setBusy(false);
    }
  }

  const columns = (rows: Node[]): Column<Node>[] => [
    { key: "name", header: "Brand", strong: true, render: (row) => row.brand_name, sortValue: (row) => row.brand_name },
    { key: "parent", header: "Parent", render: (row) => rows.find((item) => item.brand_key === row.parent_brand_key)?.brand_name ?? (row.parent_brand_key ? <code>{row.parent_brand_key}</code> : <Badge tone="brand">Top level</Badge>) },
    { key: "region", header: "Region", render: (row) => row.region || "—" },
    { key: "industry", header: "Industry", render: (row) => row.industry || "—" },
    { key: "key", header: "Key", render: (row) => <code>{row.brand_key}</code> },
  ];

  return (
    <Page width="wide">
      <PageHeader title="Brand Hierarchy" subtitle="Map parent brands and the regional or product brands under them." actions={<Button variant="primary" icon={<Plus size={15} aria-hidden="true" />} onClick={() => setOpen(true)}>Add a brand</Button>} />
      <ResourceView resource={resource} isEmpty={(rows) => rows.length === 0} empty={<EmptyState title="No brands mapped" description="Add your first brand, then add the brands that sit under it." action={<Button variant="primary" onClick={() => setOpen(true)}>Add a brand</Button>} />}>
        {(rows) => <DataTable columns={columns(rows)} rows={rows} getKey={(row) => row.brand_key} caption="Brand hierarchy" pageSize={20} />}
      </ResourceView>
      <Modal open={open} onOpenChange={setOpen} title="Add a brand">
        <form onSubmit={create} noValidate style={{ display: "grid", gap: 16 }}>
          <Field label="Brand name" value={name} error={error} maxLength={80} onChange={(event) => setName(event.target.value)} />
          <Field label="Parent brand key" value={parent} hint="Copy the key from the table. Leave empty for a top-level brand." onChange={(event) => setParent(event.target.value)} />
          <Field label="Region" value={region} maxLength={60} onChange={(event) => setRegion(event.target.value)} />
          <Field label="Industry" value={industry} maxLength={60} onChange={(event) => setIndustry(event.target.value)} />
          {failure ? <ErrorState error={failure} title="Not saved" /> : null}
          <FormActions><Button onClick={() => setOpen(false)}>Cancel</Button><Button type="submit" variant="primary" loading={busy}>Add</Button></FormActions>
        </form>
      </Modal>
    </Page>
  );
}
