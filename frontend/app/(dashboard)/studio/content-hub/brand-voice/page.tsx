"use client";

import { useState, type FormEvent } from "react";
import { Plus } from "lucide-react";
import { apiGet, apiSend } from "@/app/lib/platform-api";
import { Badge, Button, Callout, Card, EmptyState, ErrorState, Field, FieldTextarea, FormActions, Grid, KeyValue, Modal, Page, PageHeader } from "../../../_ui/kit";
import { formatDateTime } from "../../../_ui/format";
import { ResourceView, useResource, useTenant } from "../../../_ui/use-resource";

type Profile = {
  profile_key: string;
  updated_at?: string;
  fingerprint: { avg_sentence_length: number; signature_words: string[]; punctuation_intensity: number; line_break_ratio: number };
};

export default function BrandVoicePage() {
  const tenant = useTenant();
  const resource = useResource<Profile[]>(async (id) => (await apiGet<{ profiles: Profile[] }>("/ai/brand-voice/profiles", id)).profiles, []);
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [samples, setSamples] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [failure, setFailure] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  async function create(event: FormEvent) {
    event.preventDefault();
    const posts = samples.split(/\n\s*\n/).map((item) => item.trim()).filter(Boolean);
    const found: Record<string, string> = {};
    if (name.trim().length < 2) found.name = "Name this voice.";
    if (posts.length < 3) found.samples = "Paste at least three examples, with a blank line between each.";
    setErrors(found);
    if (Object.keys(found).length) return;
    setBusy(true);
    setFailure(null);
    try {
      await apiSend("/ai/brand-voice/profile", "POST", { profile_name: name.trim(), sample_posts: posts }, tenant);
      setOpen(false);
      setName("");
      setSamples("");
      resource.reload();
    } catch (caught) {
      setFailure(caught);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Page width="wide">
      <PageHeader
        title="Brand Voice"
        subtitle="Paste examples of your best writing. Nuxtron measures sentence length and the words you lean on, so you can see your style in numbers."
        actions={<Button variant="primary" icon={<Plus size={15} aria-hidden="true" />} onClick={() => setOpen(true)}>Add a voice</Button>}
      />
      <ResourceView resource={resource} isEmpty={(rows) => rows.length === 0} empty={<EmptyState title="No voice saved yet" description="Add three or more examples of your writing to measure your style." action={<Button variant="primary" onClick={() => setOpen(true)}>Add a voice</Button>} />}>
        {(rows) => (
          <Grid cols={2}>
            {rows.map((profile) => (
              <Card key={profile.profile_key}>
                <div style={{ display: "grid", gap: 14 }}>
                  <h3 style={{ margin: 0, fontSize: 17 }}>{profile.profile_key.replace(/_/g, " ")}</h3>
                  <KeyValue items={[
                    { label: "Average sentence", value: `${profile.fingerprint.avg_sentence_length} words` },
                    { label: "Questions and exclamations per post", value: profile.fingerprint.punctuation_intensity },
                    { label: "Line breaks per post", value: profile.fingerprint.line_break_ratio },
                    { label: "Saved", value: formatDateTime(profile.updated_at) },
                  ]} />
                  <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>{profile.fingerprint.signature_words.map((word) => <Badge key={word} tone="brand">{word}</Badge>)}</div>
                </div>
              </Card>
            ))}
          </Grid>
        )}
      </ResourceView>
      <Callout tone="info">This measures the writing you supply. It does not judge whether the style is good.</Callout>
      <Modal open={open} onOpenChange={setOpen} title="Add a voice">
        <form onSubmit={create} noValidate style={{ display: "grid", gap: 16 }}>
          <Field label="Voice name" value={name} error={errors.name} maxLength={60} onChange={(event) => setName(event.target.value)} />
          <FieldTextarea label="Examples of your writing" rows={9} value={samples} error={errors.samples} hint="Separate each example with a blank line. At least three." onChange={(event) => setSamples(event.target.value)} />
          {failure ? <ErrorState error={failure} title="Not saved" /> : null}
          <FormActions><Button onClick={() => setOpen(false)}>Cancel</Button><Button type="submit" variant="primary" loading={busy}>Measure and save</Button></FormActions>
        </form>
      </Modal>
    </Page>
  );
}
