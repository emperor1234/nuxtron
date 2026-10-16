"use client";

import { useState, type FormEvent } from "react";
import { apiSend } from "@/app/lib/platform-api";
import { Button, Callout, Card, ErrorState, Field, FieldSelect, FieldTextarea, FormActions, FormGrid, Section, Switch } from "./kit";
import { useTenant } from "./use-resource";

export type SectionField = {
  key: string;
  label: string;
  type?: "text" | "color" | "select" | "textarea" | "list" | "toggle" | "number" | "url";
  options?: Array<{ value: string; label: string }>;
  hint?: string;
  max?: number;
  required?: boolean;
};

type Values = Record<string, unknown>;

function toDraft(field: SectionField, value: unknown): string | boolean {
  if (field.type === "toggle") return Boolean(value);
  if (field.type === "list") return Array.isArray(value) ? value.join("\n") : "";
  return value === null || value === undefined ? "" : String(value);
}

function fromDraft(field: SectionField, draft: string | boolean): unknown {
  if (field.type === "toggle") return Boolean(draft);
  const text = String(draft).trim();
  if (field.type === "list") return text.split(/[\n,]/).map((item) => item.trim()).filter(Boolean);
  if (field.type === "number") return text === "" ? null : Number(text);
  return text;
}

const HEX = /^#[0-9a-fA-F]{6}$/;

/**
 * A titled form that saves one backend section on its own. The backend response
 * becomes the new baseline, so what is shown is always what was stored.
 */
export function SectionForm({
  title,
  description,
  endpoint,
  method = "PATCH",
  wrap,
  initial,
  fields,
  base,
  onSaved,
  saveLabel = "Save",
}: {
  title: string;
  description?: string;
  endpoint: string;
  method?: "PUT" | "PATCH" | "POST";
  /** Nest the values under this key in the request body. */
  wrap?: string;
  initial: Values;
  fields: SectionField[];
  /** Stored values that are not edited here but must be sent back unchanged. */
  base?: Values;
  onSaved?: () => void;
  saveLabel?: string;
}) {
  const tenant = useTenant();
  const build = () => Object.fromEntries(fields.map((field) => [field.key, toDraft(field, initial[field.key])])) as Record<string, string | boolean>;
  const [draft, setDraft] = useState<Record<string, string | boolean>>(build);
  const [seen, setSeen] = useState<Values>(initial);
  if (seen !== initial) {
    // The stored values changed (after a save or reload): start the form from them again.
    setSeen(initial);
    setDraft(build());
  }
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<unknown>(null);
  const [saved, setSaved] = useState(false);


  function set(key: string, value: string | boolean) {
    setDraft((current) => ({ ...current, [key]: value }));
    setSaved(false);
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    const found: Record<string, string> = {};
    for (const field of fields) {
      const text = String(draft[field.key] ?? "").trim();
      if (field.required && !text) found[field.key] = `${field.label} is required.`;
      if (field.type === "color" && text && !HEX.test(text)) found[field.key] = "Use a six-digit hex colour such as #2563c9.";
      if (field.type === "number" && text && Number.isNaN(Number(text))) found[field.key] = "Enter a number.";
    }
    setErrors(found);
    if (Object.keys(found).length) return;
    const values = Object.fromEntries(fields.map((field) => [field.key, fromDraft(field, draft[field.key] ?? "")]));
    setBusy(true);
    setFailure(null);
    try {
      await apiSend(endpoint, method, wrap ? { [wrap]: values } : { ...base, ...values }, tenant);
      setSaved(true);
      onSaved?.();
    } catch (error) {
      setFailure(error);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Section title={title} description={description}>
      <Card>
        <form onSubmit={submit} noValidate aria-label={title} style={{ display: "grid", gap: 16 }}>
          <FormGrid>
            {fields.map((field) => {
              const value = draft[field.key];
              const common = { label: field.label, hint: field.hint, error: errors[field.key] };
              if (field.type === "toggle") return <Switch key={field.key} label={field.label} checked={Boolean(value)} onChange={(next) => set(field.key, next)} />;
              if (field.type === "select") {
                return <FieldSelect key={field.key} {...common} value={String(value ?? "")} onChange={(event) => set(field.key, event.target.value)}>{field.options?.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</FieldSelect>;
              }
              if (field.type === "textarea" || field.type === "list") {
                return <FieldTextarea key={field.key} {...common} rows={field.type === "list" ? 4 : 3} maxLength={field.max} value={String(value ?? "")} hint={field.type === "list" ? (field.hint ?? "One per line.") : field.hint} onChange={(event) => set(field.key, event.target.value)} />;
              }
              if (field.type === "color") {
                const hex = String(value ?? "");
                return (
                  <div key={field.key} style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
                    <div style={{ flex: 1 }}><Field {...common} value={hex} maxLength={7} onChange={(event) => set(field.key, event.target.value)} /></div>
                    <span aria-hidden="true" style={{ width: 40, height: 40, borderRadius: 8, marginTop: 24, border: "1px solid var(--nx-line, #d9dce5)", background: HEX.test(hex) ? hex : "transparent" }} />
                  </div>
                );
              }
              return <Field key={field.key} {...common} type={field.type === "number" ? "number" : field.type === "url" ? "url" : "text"} maxLength={field.max} value={String(value ?? "")} onChange={(event) => set(field.key, event.target.value)} />;
            })}
          </FormGrid>
          {failure ? <ErrorState error={failure} title="Not saved" /> : null}
          {saved ? <Callout tone="success">Saved.</Callout> : null}
          <FormActions><Button type="submit" variant="primary" loading={busy}>{saveLabel}</Button></FormActions>
        </form>
      </Card>
    </Section>
  );
}
