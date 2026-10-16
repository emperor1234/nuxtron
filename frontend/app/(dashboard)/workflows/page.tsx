"use client";

import { useState, type FormEvent } from "react";
import { Plus, Trash2 } from "lucide-react";
import { apiGet, apiSend } from "@/app/lib/platform-api";
import { Button, Callout, ConfirmModal, DataTable, EmptyState, ErrorState, Field, FieldSelect, FieldTextarea, FormActions, Modal, Page, PageHeader, Switch, type Column } from "../_ui/kit";
import { formatDate } from "../_ui/format";
import { ResourceView, useResource, useTenant } from "../_ui/use-resource";

type Workflow = { id: number; name: string; description?: string; trigger: { trigger_type: string }; step_count: number; status: string; enrollment_count: number; execution_count: number; created_at?: string };
type StepDraft = { action: string; delay: string; config: string };

const TRIGGERS = ["manual", "contact_created", "deal_stage_changed", "form_submitted", "ticket_created", "survey_response", "date_based", "tag_added", "property_changed", "webhook", "api_event"];
const ACTIONS = ["send_email", "update_property", "add_tag", "remove_tag", "notify_rep", "create_task", "send_webhook", "delay", "enroll_sequence", "create_ticket", "add_to_list"];
const label = (value: string) => value.replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase());

export default function WorkflowsPage() {
  const tenant = useTenant();
  const resource = useResource<Workflow[]>(async (id) => (await apiGet<{ workflows: Workflow[] }>("/workflows?limit=100", id)).workflows, []);
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [trigger, setTrigger] = useState("manual");
  const [steps, setSteps] = useState<StepDraft[]>([{ action: "send_email", delay: "0", config: "" }]);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [failure, setFailure] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const [removing, setRemoving] = useState<Workflow | null>(null);

  function updateStep(index: number, patch: Partial<StepDraft>) {
    setSteps((current) => current.map((step, i) => (i === index ? { ...step, ...patch } : step)));
  }

  async function create(event: FormEvent) {
    event.preventDefault();
    const found: Record<string, string> = {};
    if (!name.trim()) found.name = "Name the workflow.";
    const built = steps.map((step, index) => {
      let config: Record<string, unknown> = {};
      if (step.config.trim()) {
        try {
          const parsed: unknown = JSON.parse(step.config);
          if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) throw new Error("not an object");
          config = parsed as Record<string, unknown>;
        } catch {
          found[`config-${index}`] = "Settings must be a JSON object, for example {\"subject\": \"Welcome\"}.";
        }
      }
      const delay = Number(step.delay || 0);
      if (!Number.isInteger(delay) || delay < 0 || delay > 8760) found[`delay-${index}`] = "Use whole hours from 0 to 8760.";
      return { step_id: `step_${index + 1}`, action_type: step.action, config, delay_hours: delay, next_step_id: index < steps.length - 1 ? `step_${index + 2}` : "" };
    });
    setErrors(found);
    if (Object.keys(found).length) return;
    setBusy(true);
    setFailure(null);
    try {
      await apiSend("/workflows", "POST", { name: name.trim(), description: description.trim(), trigger: { trigger_type: trigger, conditions: [] }, steps: built }, tenant);
      setOpen(false);
      setName("");
      setDescription("");
      setSteps([{ action: "send_email", delay: "0", config: "" }]);
      resource.reload();
    } catch (caught) {
      setFailure(caught);
    } finally {
      setBusy(false);
    }
  }

  async function toggle(workflow: Workflow, active: boolean) {
    setFailure(null);
    try {
      await apiSend(`/workflows/${workflow.id}/toggle?active=${active}`, "PATCH", undefined, tenant);
      resource.reload();
    } catch (caught) {
      setFailure(caught);
    }
  }

  async function remove() {
    if (!removing) return;
    try {
      await apiSend(`/workflows/${removing.id}`, "DELETE", undefined, tenant);
      resource.reload();
    } catch (caught) {
      setFailure(caught);
    }
    setRemoving(null);
  }

  const columns: Column<Workflow>[] = [
    { key: "name", header: "Workflow", strong: true, render: (row) => <span>{row.name}{row.description ? <><br /><span style={{ color: "var(--nx-muted)", fontWeight: 400 }}>{row.description}</span></> : null}</span>, sortValue: (row) => row.name },
    { key: "trigger", header: "Starts when", render: (row) => label(row.trigger.trigger_type) },
    { key: "steps", header: "Steps", numeric: true, render: (row) => row.step_count, sortValue: (row) => row.step_count },
    { key: "enrolled", header: "Enrolled", numeric: true, render: (row) => row.enrollment_count, sortValue: (row) => row.enrollment_count },
    { key: "status", header: "Active", render: (row) => <Switch label={row.status === "active" ? "On" : "Off"} checked={row.status === "active"} onChange={(next) => void toggle(row, next)} /> },
    { key: "created", header: "Created", render: (row) => formatDate(row.created_at), sortValue: (row) => row.created_at ?? "" },
    { key: "x", header: "", render: (row) => <Button size="sm" variant="ghost" icon={<Trash2 size={14} aria-hidden="true" />} aria-label={`Delete ${row.name}`} onClick={() => setRemoving(row)}>Delete</Button> },
  ];

  return (
    <Page width="wide">
      <PageHeader title="Workflows" subtitle="Define what should happen after an event, step by step." actions={<Button variant="primary" icon={<Plus size={15} aria-hidden="true" />} onClick={() => setOpen(true)}>New workflow</Button>} />
      {failure && !open ? <ErrorState error={failure} title="The change failed" /> : null}
      <ResourceView resource={resource} isEmpty={(rows) => rows.length === 0} empty={<EmptyState title="No workflows yet" description="Create a workflow to describe a follow-up that should run on its own." action={<Button variant="primary" onClick={() => setOpen(true)}>New workflow</Button>} />}>
        {(rows) => <DataTable columns={columns} rows={rows} getKey={(row) => row.id} caption="Workflows" pageSize={15} />}
      </ResourceView>
      <Callout tone="info">Steps that send messages only work once the matching channel, such as email, is connected.</Callout>
      <Modal open={open} onOpenChange={setOpen} title="New workflow">
        <form onSubmit={create} noValidate style={{ display: "grid", gap: 16 }}>
          <Field label="Name" value={name} error={errors.name} maxLength={200} onChange={(event) => setName(event.target.value)} />
          <Field label="Description" value={description} maxLength={1000} onChange={(event) => setDescription(event.target.value)} />
          <FieldSelect label="Starts when" value={trigger} onChange={(event) => setTrigger(event.target.value)}>{TRIGGERS.map((item) => <option key={item} value={item}>{label(item)}</option>)}</FieldSelect>
          {steps.map((step, index) => (
            <fieldset key={index} style={{ border: "1px solid var(--nx-line, #d9dce5)", borderRadius: 10, padding: 14, display: "grid", gap: 12, margin: 0 }}>
              <legend style={{ padding: "0 6px", fontWeight: 600 }}>Step {index + 1}</legend>
              <FieldSelect label="Action" value={step.action} onChange={(event) => updateStep(index, { action: event.target.value })}>{ACTIONS.map((item) => <option key={item} value={item}>{label(item)}</option>)}</FieldSelect>
              <Field label="Wait before this step (hours)" inputMode="numeric" value={step.delay} error={errors[`delay-${index}`]} onChange={(event) => updateStep(index, { delay: event.target.value })} />
              <FieldTextarea label="Settings (JSON, optional)" rows={2} value={step.config} error={errors[`config-${index}`]} onChange={(event) => updateStep(index, { config: event.target.value })} />
              {steps.length > 1 ? <div><Button size="sm" onClick={() => setSteps((current) => current.filter((_, i) => i !== index))}>Remove step</Button></div> : null}
            </fieldset>
          ))}
          {steps.length < 20 ? <div><Button onClick={() => setSteps((current) => [...current, { action: "send_email", delay: "0", config: "" }])} icon={<Plus size={14} aria-hidden="true" />}>Add a step</Button></div> : null}
          {failure ? <ErrorState error={failure} title="Not saved" /> : null}
          <FormActions><Button onClick={() => setOpen(false)}>Cancel</Button><Button type="submit" variant="primary" loading={busy}>Create workflow</Button></FormActions>
        </form>
      </Modal>
      <ConfirmModal open={Boolean(removing)} onOpenChange={(next) => !next && setRemoving(null)} title="Delete this workflow?" description={`"${removing?.name ?? ""}" and its history are removed.`} onConfirm={() => void remove()} />
    </Page>
  );
}
