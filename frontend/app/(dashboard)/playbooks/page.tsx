"use client";

import { useState, type FormEvent } from "react";
import { Eye, Plus } from "lucide-react";
import { apiGet, apiSend } from "@/app/lib/platform-api";
import { Badge, Button, Callout, Card, DataTable, Drawer, EmptyState, ErrorState, Field, FieldTextarea, FormActions, Grid, Modal, Page, PageHeader, Section, Tabs, type Column } from "../_ui/kit";
import { formatDateTime } from "../_ui/format";
import { ResourceView, useResource, useTenant } from "../_ui/use-resource";

type Playbook = { id: string; name: string; vertical?: string; description: string; built_in?: boolean; steps: string[]; integrations?: string[]; time_to_value_days?: number };
type Run = { id: string; playbook_name?: string; status: string; steps_total?: number; created_at?: string; dry_run?: boolean };

export default function PlaybooksPage() {
  const tenant = useTenant();
  const [tab, setTab] = useState("library");
  const playbooks = useResource<Playbook[]>(async (id) => (await apiGet<{ playbooks: Playbook[] }>("/playbooks", id)).playbooks, []);
  const runs = useResource<Run[]>(async (id) => (await apiGet<{ runs: Run[] }>("/playbooks/runs/list", id)).runs, [tab]);
  const [selected, setSelected] = useState<Playbook | null>(null);
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [steps, setSteps] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [failure, setFailure] = useState<unknown>(null);
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);

  async function preview(playbook: Playbook) {
    setFailure(null);
    setNotice("");
    try {
      const result = await apiSend<{ steps_total: number }>("/playbooks/run", "POST", { playbook_id: playbook.id, dry_run: true }, tenant);
      setNotice(`Preview saved for "${playbook.name}": ${result.steps_total} steps. Nothing was executed.`);
      runs.reload();
    } catch (caught) {
      setFailure(caught);
    }
  }

  async function create(event: FormEvent) {
    event.preventDefault();
    const list = steps.split("\n").map((line) => line.trim()).filter(Boolean);
    const found: Record<string, string> = {};
    if (name.trim().length < 2) found.name = "Name the playbook (2 characters or more).";
    if (description.trim().length < 5) found.description = "Describe it in 5 characters or more.";
    if (!list.length) found.steps = "Add at least one step.";
    setErrors(found);
    if (Object.keys(found).length) return;
    setBusy(true);
    setFailure(null);
    try {
      await apiSend("/playbooks", "POST", { name: name.trim(), description: description.trim(), steps: list }, tenant);
      setOpen(false);
      setName("");
      setDescription("");
      setSteps("");
      playbooks.reload();
    } catch (caught) {
      setFailure(caught);
    } finally {
      setBusy(false);
    }
  }

  const runColumns: Column<Run>[] = [
    { key: "name", header: "Playbook", strong: true, render: (row) => row.playbook_name || "—" },
    { key: "status", header: "Result", render: (row) => <Badge>{row.status === "dry_run_preview" ? "Preview only" : row.status}</Badge> },
    { key: "steps", header: "Steps", numeric: true, render: (row) => row.steps_total ?? "—" },
    { key: "when", header: "When", render: (row) => formatDateTime(row.created_at), sortValue: (row) => row.created_at ?? "" },
  ];

  return (
    <Page width="wide">
      <PageHeader
        title="Playbooks"
        subtitle="Step-by-step plans for common marketing jobs. Use them as checklists or save your own."
        actions={<Button variant="primary" icon={<Plus size={15} aria-hidden="true" />} onClick={() => setOpen(true)}>New playbook</Button>}
        tabs={<Tabs items={[{ id: "library", label: "Library" }, { id: "previews", label: "Previews" }]} value={tab} onChange={setTab} label="Playbook sections" />}
      />
      {notice ? <Callout tone="success">{notice}</Callout> : null}
      {failure && !open ? <ErrorState error={failure} title="That did not work" /> : null}
      {tab === "library" ? (
        <ResourceView resource={playbooks} isEmpty={(rows) => rows.length === 0} empty={<EmptyState title="No playbooks" description="Create the first one." />}>
          {(rows) => (
            <Grid cols={2}>
              {rows.map((playbook) => (
                <Card key={playbook.id}>
                  <div style={{ display: "grid", gap: 10 }}>
                    <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
                      <h3 style={{ margin: 0, fontSize: 16 }}>{playbook.name}</h3>
                      {playbook.built_in ? <Badge tone="brand">Template</Badge> : <Badge>Yours</Badge>}
                    </div>
                    <p style={{ margin: 0, color: "var(--nx-muted)", fontSize: 14 }}>{playbook.description}</p>
                    <div style={{ display: "flex", gap: 8 }}>
                      <Button size="sm" onClick={() => setSelected(playbook)}>View steps</Button>
                      <Button size="sm" icon={<Eye size={14} aria-hidden="true" />} onClick={() => void preview(playbook)}>Preview run</Button>
                    </div>
                  </div>
                </Card>
              ))}
            </Grid>
          )}
        </ResourceView>
      ) : (
        <Section title="Saved previews" description="Playbooks are not executed automatically. A preview records the plan only.">
          <ResourceView resource={runs} isEmpty={(rows) => rows.length === 0} empty={<EmptyState title="No previews yet" description="Preview a playbook from the library." />}>
            {(rows) => <DataTable columns={runColumns} rows={rows} getKey={(row) => row.id} caption="Playbook previews" pageSize={15} />}
          </ResourceView>
        </Section>
      )}
      <Drawer open={Boolean(selected)} onOpenChange={(next) => !next && setSelected(null)} title={selected?.name ?? ""} description={selected?.description}>
        {selected ? (
          <ol style={{ margin: 0, paddingLeft: 20, display: "grid", gap: 8, fontSize: 14.5 }}>{selected.steps.map((step) => <li key={step}>{step}</li>)}</ol>
        ) : null}
      </Drawer>
      <Modal open={open} onOpenChange={setOpen} title="New playbook">
        <form onSubmit={create} noValidate style={{ display: "grid", gap: 16 }}>
          <Field label="Name" value={name} error={errors.name} maxLength={180} onChange={(event) => setName(event.target.value)} />
          <FieldTextarea label="What it is for" rows={2} value={description} error={errors.description} maxLength={1000} onChange={(event) => setDescription(event.target.value)} />
          <FieldTextarea label="Steps" rows={6} value={steps} error={errors.steps} hint="One step per line." onChange={(event) => setSteps(event.target.value)} />
          {failure ? <ErrorState error={failure} title="Not saved" /> : null}
          <FormActions><Button onClick={() => setOpen(false)}>Cancel</Button><Button type="submit" variant="primary" loading={busy}>Save playbook</Button></FormActions>
        </form>
      </Modal>
    </Page>
  );
}
