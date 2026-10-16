"use client";

import { useState, type FormEvent } from "react";
import { Plus, Trash2 } from "lucide-react";
import { apiGet, apiSend } from "@/app/lib/platform-api";
import { Badge, Button, ConfirmModal, DataTable, EmptyState, ErrorState, Field, FieldSelect, FieldTextarea, FormActions, Kpi, KpiGrid, Modal, Page, PageHeader, Section, Tabs, type Column } from "../../_ui/kit";
import { SectionForm, type SectionField } from "../../_ui/section-form";
import { formatDateTime, truncate } from "../../_ui/format";
import { ResourceView, useResource, useTenant } from "../../_ui/use-resource";

type Kit = {
  colors: Record<string, string>;
  fonts: Record<string, Record<string, unknown>>;
  logos: Record<string, string>;
  voice: Record<string, unknown>;
  messaging: Record<string, unknown>;
  writing_rules: Record<string, unknown>;
  knowledge_base_count: number;
};
type Entry = { id: string; entry_type: string; label?: string; content: string; created_at?: string };

const COLOR_FIELDS: SectionField[] = ["primary", "secondary", "accent", "background", "text", "muted"].map((key) => ({ key, label: key.charAt(0).toUpperCase() + key.slice(1), type: "color" as const }));
const FONT_FIELDS: SectionField[] = [
  { key: "family", label: "Font family", required: true, max: 60 },
  { key: "weight", label: "Weight", type: "select", options: ["300", "400", "500", "600", "700", "800", "900"].map((value) => ({ value, label: value })) },
  { key: "size_px", label: "Size (px)", type: "number" },
];
const LOGO_FIELDS: SectionField[] = [
  { key: "main", label: "Main logo URL", type: "url" },
  { key: "icon", label: "Icon URL", type: "url" },
  { key: "dark_variant", label: "Logo for dark backgrounds", type: "url" },
  { key: "light_variant", label: "Logo for light backgrounds", type: "url" },
];
const TONES = ["professional", "friendly", "casual", "bold", "playful", "authoritative", "empathetic"].map((value) => ({ value, label: value.charAt(0).toUpperCase() + value.slice(1) }));
const VOICE_FIELDS: SectionField[] = [
  { key: "tone_preset", label: "Tone", type: "select", options: TONES },
  { key: "formality", label: "Formality", type: "select", options: ["casual", "neutral", "formal"].map((value) => ({ value, label: value.charAt(0).toUpperCase() + value.slice(1) })) },
  { key: "emotion", label: "Emotion", type: "text", max: 40 },
  { key: "custom_description", label: "Describe your voice in your own words", type: "textarea", max: 500 },
];
const MESSAGING_FIELDS: SectionField[] = [
  { key: "brand_name", label: "Brand name", max: 80 },
  { key: "tagline", label: "Tagline", max: 140 },
  { key: "value_proposition", label: "Value proposition", type: "textarea", max: 400 },
  { key: "elevator_pitch", label: "Elevator pitch", type: "textarea", max: 600 },
  { key: "target_audience", label: "Target audience", type: "textarea", max: 400 },
];
const RULE_FIELDS: SectionField[] = [
  { key: "terms_to_use", label: "Words and phrases to use", type: "list" },
  { key: "terms_to_avoid", label: "Words and phrases to avoid", type: "list" },
  { key: "preferred_sentences", label: "Sentence length", type: "select", options: ["short", "medium", "long"].map((value) => ({ value, label: value.charAt(0).toUpperCase() + value.slice(1) })) },
  { key: "use_oxford_comma", label: "Use the Oxford comma", type: "toggle" },
  { key: "capitalize_brand_name", label: "Always capitalise the brand name", type: "toggle" },
  { key: "notes", label: "Other notes", type: "textarea", max: 600 },
];

const TABS = [
  { id: "visual", label: "Colours and type" },
  { id: "logos", label: "Logos" },
  { id: "voice", label: "Voice" },
  { id: "messaging", label: "Messaging" },
  { id: "rules", label: "Writing rules" },
  { id: "knowledge", label: "Knowledge base" },
];

function KnowledgeBase({ onChange }: { onChange: () => void }) {
  const tenant = useTenant();
  const entries = useResource<Entry[]>(async (id) => (await apiGet<{ entries: Entry[] }>("/brand-kit/knowledge-base", id)).entries, []);
  const [open, setOpen] = useState(false);
  const [type, setType] = useState("text");
  const [label, setLabel] = useState("");
  const [content, setContent] = useState("");
  const [error, setError] = useState("");
  const [failure, setFailure] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const [removing, setRemoving] = useState<Entry | null>(null);

  async function add(event: FormEvent) {
    event.preventDefault();
    if (!content.trim()) return setError("Add the text, link or title.");
    setBusy(true);
    setFailure(null);
    try {
      await apiSend("/brand-kit/knowledge-base", "POST", { entry_type: type, content: content.trim(), label: label.trim() || undefined }, tenant);
      setOpen(false);
      setContent("");
      setLabel("");
      setError("");
      entries.reload();
      onChange();
    } catch (caught) {
      setFailure(caught);
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    if (!removing) return;
    try {
      await apiSend(`/brand-kit/knowledge-base/${encodeURIComponent(removing.id)}`, "DELETE", undefined, tenant);
      setRemoving(null);
      entries.reload();
      onChange();
    } catch (caught) {
      setRemoving(null);
      setFailure(caught);
    }
  }

  const columns: Column<Entry>[] = [
    { key: "label", header: "Entry", strong: true, render: (row) => row.label || row.entry_type },
    { key: "type", header: "Type", render: (row) => <Badge>{row.entry_type}</Badge> },
    { key: "content", header: "Content", render: (row) => truncate(row.content, 120) },
    { key: "when", header: "Added", render: (row) => formatDateTime(row.created_at) },
    { key: "actions", header: "", render: (row) => <Button size="sm" variant="ghost" icon={<Trash2 size={14} aria-hidden="true" />} onClick={() => setRemoving(row)} aria-label={`Remove ${row.label || row.entry_type}`}>Remove</Button> },
  ];

  return (
    <Section title="Knowledge base" description="Facts, links and document titles that describe your brand." actions={<Button variant="primary" icon={<Plus size={15} aria-hidden="true" />} onClick={() => setOpen(true)}>Add entry</Button>}>
      {failure ? <ErrorState error={failure} title="Not saved" /> : null}
      <ResourceView resource={entries} isEmpty={(rows) => rows.length === 0} empty={<EmptyState title="Nothing here yet" description="Add the facts you want every piece of content to respect." />}>
        {(rows) => <DataTable columns={columns} rows={rows} getKey={(row) => row.id} caption="Knowledge base entries" pageSize={10} />}
      </ResourceView>
      <Modal open={open} onOpenChange={setOpen} title="Add to the knowledge base">
        <form onSubmit={add} noValidate style={{ display: "grid", gap: 16 }}>
          <FieldSelect label="Type" value={type} onChange={(event) => setType(event.target.value)}>
            <option value="text">Text</option><option value="url">Link</option><option value="pdf_title">Document title</option>
          </FieldSelect>
          <Field label="Label (optional)" value={label} maxLength={80} onChange={(event) => setLabel(event.target.value)} />
          <FieldTextarea label="Content" rows={4} value={content} error={error} onChange={(event) => setContent(event.target.value)} />
          <FormActions><Button onClick={() => setOpen(false)}>Cancel</Button><Button type="submit" variant="primary" loading={busy}>Add</Button></FormActions>
        </form>
      </Modal>
      <ConfirmModal open={Boolean(removing)} onOpenChange={(next) => !next && setRemoving(null)} title="Remove this entry?" description="The entry is deleted from your brand kit." confirmLabel="Remove" onConfirm={() => void remove()} />
    </Section>
  );
}

export default function BrandKitPage() {
  const [tab, setTab] = useState("visual");
  const resource = useResource<Kit>(async (tenant) => (await apiGet<{ brand_kit: Kit }>("/brand-kit", tenant)).brand_kit, []);

  return (
    <Page width="wide">
      <PageHeader title="Brand Kit" subtitle="Your colours, type, logos, voice and writing rules. Saved here, applied to content you generate." />
      <ResourceView resource={resource}>
        {(kit) => (
          <>
            <KpiGrid>
              <Kpi label="Knowledge base entries" value={kit.knowledge_base_count} />
              <Kpi label="Tone" value={String(kit.voice.tone_preset ?? "—")} />
            </KpiGrid>
            <Tabs items={TABS} value={tab} onChange={setTab} label="Brand kit sections" />
            {tab === "visual" ? (
              <>
                <SectionForm title="Colours" endpoint="/brand-kit/colors" initial={kit.colors} fields={COLOR_FIELDS} onSaved={resource.reload} />
                {(["heading", "body", "display"] as const).map((role) => (
                  <SectionForm key={role} title={`${role.charAt(0).toUpperCase() + role.slice(1)} font`} endpoint="/brand-kit/fonts" wrap={role} initial={kit.fonts[role] ?? {}} fields={FONT_FIELDS} onSaved={resource.reload} />
                ))}
              </>
            ) : null}
            {tab === "logos" ? <SectionForm title="Logos" description="Link to hosted image files." endpoint="/brand-kit/logos" initial={kit.logos} fields={LOGO_FIELDS} onSaved={resource.reload} /> : null}
            {tab === "voice" ? <SectionForm title="Voice" endpoint="/brand-kit/voice" initial={kit.voice} fields={VOICE_FIELDS} onSaved={resource.reload} /> : null}
            {tab === "messaging" ? <SectionForm title="Messaging" endpoint="/brand-kit/messaging" initial={kit.messaging} fields={MESSAGING_FIELDS} onSaved={resource.reload} /> : null}
            {tab === "rules" ? <SectionForm title="Writing rules" endpoint="/brand-kit/writing-rules" initial={kit.writing_rules} fields={RULE_FIELDS} onSaved={resource.reload} /> : null}
            {tab === "knowledge" ? <KnowledgeBase onChange={resource.reload} /> : null}
          </>
        )}
      </ResourceView>
    </Page>
  );
}
