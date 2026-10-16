"use client";

import { useState, type FormEvent } from "react";
import { Plus, Trash2 } from "lucide-react";
import { apiGet, apiSend } from "@/app/lib/platform-api";
import { Badge, Button, ConfirmModal, DataTable, Drawer, EmptyState, ErrorState, Field, FieldSelect, FormActions, Modal, Page, PageHeader, Section, type Column } from "../../_ui/kit";
import { formatDate } from "../../_ui/format";
import { ResourceView, useResource, useTenant } from "../../_ui/use-resource";

type Brand = { id: string; name: string; description?: string; website?: string; status?: string; created_at?: string };
type Asset = { id: string; name: string; asset_type: string; url: string; category?: string };

const ASSET_TYPES = ["logo", "image", "video", "font", "document"];

function Assets({ brand }: { brand: Brand }) {
  const tenant = useTenant();
  const base = `/api/v1/brands/${encodeURIComponent(brand.id)}/assets`;
  const assets = useResource<Asset[]>(async (id) => {
    const response = await apiGet<Asset[] | { assets?: Asset[] }>(base, id);
    return Array.isArray(response) ? response : (response.assets ?? []);
  }, [brand.id]);
  const [name, setName] = useState("");
  const [url, setUrl] = useState("");
  const [type, setType] = useState("logo");
  const [error, setError] = useState("");
  const [failure, setFailure] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const [removing, setRemoving] = useState<Asset | null>(null);

  async function add(event: FormEvent) {
    event.preventDefault();
    if (!name.trim() || !/^https?:\/\//i.test(url.trim())) return setError("Give the asset a name and a full http(s) link.");
    setError("");
    setBusy(true);
    setFailure(null);
    try {
      await apiSend(`${base}?${new URLSearchParams({ name: name.trim(), asset_type: type, url: url.trim() })}`, "POST", undefined, tenant);
      setName("");
      setUrl("");
      assets.reload();
    } catch (caught) {
      setFailure(caught);
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    if (!removing) return;
    try {
      await apiSend(`${base}/${encodeURIComponent(removing.id)}`, "DELETE", undefined, tenant);
      assets.reload();
    } catch (caught) {
      setFailure(caught);
    }
    setRemoving(null);
  }

  const columns: Column<Asset>[] = [
    { key: "name", header: "Name", strong: true, render: (row) => <a href={row.url} target="_blank" rel="noreferrer noopener">{row.name}</a> },
    { key: "type", header: "Type", render: (row) => <Badge>{row.asset_type}</Badge> },
    { key: "x", header: "", render: (row) => <Button size="sm" variant="ghost" icon={<Trash2 size={14} aria-hidden="true" />} aria-label={`Remove ${row.name}`} onClick={() => setRemoving(row)}>Remove</Button> },
  ];

  return (
    <div style={{ display: "grid", gap: 20 }}>
      <form onSubmit={add} noValidate aria-label="Add asset" style={{ display: "grid", gap: 12 }}>
        <Field label="Asset name" value={name} onChange={(event) => setName(event.target.value)} maxLength={80} />
        <Field label="Link to the file" type="url" value={url} error={error} onChange={(event) => setUrl(event.target.value)} />
        <FieldSelect label="Type" value={type} onChange={(event) => setType(event.target.value)}>{ASSET_TYPES.map((item) => <option key={item} value={item}>{item}</option>)}</FieldSelect>
        <FormActions><Button type="submit" variant="primary" loading={busy}>Add asset</Button></FormActions>
      </form>
      {failure ? <ErrorState error={failure} title="The change failed" /> : null}
      <ResourceView resource={assets} isEmpty={(rows) => rows.length === 0} empty={<EmptyState title="No assets" description="Add logos, images and fonts for this brand." />}>
        {(rows) => <DataTable columns={columns} rows={rows} getKey={(row) => row.id} caption={`${brand.name} assets`} />}
      </ResourceView>
      <ConfirmModal open={Boolean(removing)} onOpenChange={(next) => !next && setRemoving(null)} title="Remove this asset?" description="The link is removed from this brand." confirmLabel="Remove" onConfirm={() => void remove()} />
    </div>
  );
}

export default function BrandsPage() {
  const tenant = useTenant();
  const resource = useResource<Brand[]>(async (id) => (await apiGet<{ brands: Brand[] }>("/api/v1/brands", id)).brands, []);
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [website, setWebsite] = useState("");
  const [error, setError] = useState("");
  const [failure, setFailure] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const [selected, setSelected] = useState<Brand | null>(null);

  async function create(event: FormEvent) {
    event.preventDefault();
    if (name.trim().length < 2) return setError("Give the brand a name.");
    setError("");
    setBusy(true);
    setFailure(null);
    try {
      const query = new URLSearchParams({ name: name.trim() });
      if (description.trim()) query.set("description", description.trim());
      if (website.trim()) query.set("website", website.trim());
      await apiSend(`/api/v1/brands?${query}`, "POST", undefined, tenant);
      setOpen(false);
      setName("");
      setDescription("");
      setWebsite("");
      resource.reload();
    } catch (caught) {
      setFailure(caught);
    } finally {
      setBusy(false);
    }
  }

  const columns: Column<Brand>[] = [
    { key: "name", header: "Brand", strong: true, render: (row) => row.name, sortValue: (row) => row.name },
    { key: "website", header: "Website", render: (row) => row.website || "—" },
    { key: "status", header: "Status", render: (row) => <Badge tone={row.status === "active" ? "success" : "neutral"}>{row.status ?? "active"}</Badge> },
    { key: "created", header: "Created", render: (row) => formatDate(row.created_at), sortValue: (row) => row.created_at ?? "" },
  ];

  return (
    <Page width="wide">
      <PageHeader title="Brands" subtitle="Keep one record per brand you manage, with its own assets." actions={<Button variant="primary" icon={<Plus size={15} aria-hidden="true" />} onClick={() => setOpen(true)}>New brand</Button>} />
      <Section title="Your brands">
        <ResourceView resource={resource} isEmpty={(rows) => rows.length === 0} empty={<EmptyState title="No brands yet" description="Create a brand to store its logos and files." action={<Button variant="primary" onClick={() => setOpen(true)}>New brand</Button>} />}>
          {(rows) => <DataTable columns={columns} rows={rows} getKey={(row) => row.id} onRowClick={setSelected} caption="Brands" pageSize={15} />}
        </ResourceView>
      </Section>
      <Modal open={open} onOpenChange={setOpen} title="New brand">
        <form onSubmit={create} noValidate style={{ display: "grid", gap: 16 }}>
          <Field label="Name" value={name} error={error} maxLength={80} onChange={(event) => setName(event.target.value)} />
          <Field label="Description" value={description} maxLength={200} onChange={(event) => setDescription(event.target.value)} />
          <Field label="Website" type="url" value={website} onChange={(event) => setWebsite(event.target.value)} />
          {failure ? <ErrorState error={failure} title="Not created" /> : null}
          <FormActions><Button onClick={() => setOpen(false)}>Cancel</Button><Button type="submit" variant="primary" loading={busy}>Create</Button></FormActions>
        </form>
      </Modal>
      <Drawer open={Boolean(selected)} onOpenChange={(next) => !next && setSelected(null)} title={selected?.name ?? ""} description={selected?.description}>
        {selected ? <Assets brand={selected} /> : null}
      </Drawer>
    </Page>
  );
}
