"use client";

import { useState, type FormEvent } from "react";
import { Copy, Sparkles } from "lucide-react";
import {
  Badge,
  Button,
  Callout,
  Card,
  EmptyState,
  ErrorState,
  Field,
  FieldSelect,
  FieldTextarea,
  Page,
  PageHeader,
  Skeleton,
  Split,
  Switch,
} from "../../_ui/kit";
import { useMutation } from "../../_ui/use-resource";
import { ResultView } from "./result-view";
import type { FieldSpec, ToolSpec } from "./specs";
import styles from "./tool.module.css";

type Values = Record<string, string | boolean>;
type Errors = Record<string, string>;

function initialValues(fields: readonly FieldSpec[]): Values {
  const values: Values = {};
  for (const field of fields) {
    values[field.name] = field.kind === "toggle" ? Boolean(field.initial) : field.initial !== undefined ? String(field.initial) : "";
  }
  return values;
}

function splitList(text: string): string[] {
  return text
    .split(/\r?\n|,/)
    .map((item) => item.trim())
    .filter(Boolean);
}

/** Validates the form and builds the exact request body the backend model expects. */
function buildPayload(spec: ToolSpec, values: Values): { payload: Record<string, unknown>; errors: Errors } {
  const payload: Record<string, unknown> = {};
  const errors: Errors = {};

  for (const field of spec.fields) {
    const raw = values[field.name];
    if (field.kind === "toggle") {
      payload[field.name] = Boolean(raw);
      continue;
    }
    const text = typeof raw === "string" ? raw.trim() : "";
    if (!text) {
      if (field.required) errors[field.name] = `${field.label} is required.`;
      continue;
    }
    if (field.kind === "number") {
      const parsed = Number(text);
      if (!Number.isFinite(parsed) || !Number.isInteger(parsed)) {
        errors[field.name] = `${field.label} must be a whole number.`;
      } else if (field.min !== undefined && parsed < field.min) {
        errors[field.name] = `${field.label} must be at least ${field.min}.`;
      } else if (field.max !== undefined && parsed > field.max) {
        errors[field.name] = `${field.label} must be ${field.max} or less.`;
      } else {
        payload[field.name] = parsed;
      }
    } else if (field.kind === "list") {
      payload[field.name] = splitList(text);
    } else {
      if (field.max !== undefined && text.length > field.max) {
        errors[field.name] = `${field.label} must be ${field.max.toLocaleString()} characters or fewer.`;
      } else {
        payload[field.name] = text;
      }
    }
  }

  for (const group of spec.oneOf ?? []) {
    const filled = group.some((name) => payload[name] !== undefined && payload[name] !== "");
    if (!filled) {
      const labels = group.map((name) => spec.fields.find((field) => field.name === name)?.label ?? name);
      const message = `Provide ${labels.join(" or ")}.`;
      for (const name of group) errors[name] = errors[name] ?? message;
    }
  }

  return { payload, errors };
}

function FieldControl({
  field,
  value,
  error,
  onChange,
}: {
  field: FieldSpec;
  value: string | boolean;
  error?: string;
  onChange: (next: string | boolean) => void;
}) {
  const shared = { label: field.label, hint: field.hint, error, required: field.required };
  switch (field.kind) {
    case "textarea":
    case "list":
      return (
        <FieldTextarea
          {...shared}
          rows={field.rows ?? (field.kind === "list" ? 4 : 5)}
          placeholder={field.placeholder}
          maxLength={field.max ? field.max + 200 : undefined}
          value={String(value)}
          onChange={(event) => onChange(event.target.value)}
          hint={field.hint ?? (field.kind === "list" ? "One per line." : undefined)}
        />
      );
    case "select":
      return (
        <FieldSelect {...shared} value={String(value)} onChange={(event) => onChange(event.target.value)}>
          {field.options?.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </FieldSelect>
      );
    case "toggle":
      return <Switch label={field.label} checked={Boolean(value)} onChange={onChange} />;
    case "number":
      return (
        <Field
          {...shared}
          type="number"
          inputMode="numeric"
          min={field.min}
          max={field.max}
          value={String(value)}
          onChange={(event) => onChange(event.target.value)}
        />
      );
    default:
      return (
        <Field
          {...shared}
          type="text"
          placeholder={field.placeholder}
          maxLength={field.max ? field.max + 50 : undefined}
          value={String(value)}
          onChange={(event) => onChange(event.target.value)}
        />
      );
  }
}

/**
 * One page for every SEO analysis tool. The spec supplies the real route and
 * fields; this component handles validation, the request, and honest
 * loading / error / result states.
 */
export function SeoToolPage({ spec }: { spec: ToolSpec }) {
  const [values, setValues] = useState<Values>(() => initialValues(spec.fields));
  const [errors, setErrors] = useState<Errors>({});
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [copied, setCopied] = useState(false);
  const mutation = useMutation<Record<string, unknown>, Record<string, unknown>>(spec.endpoint);

  async function submit(event: FormEvent) {
    event.preventDefault();
    const { payload, errors: found } = buildPayload(spec, values);
    setErrors(found);
    if (Object.keys(found).length > 0) return;
    setResult(null);
    const response = await mutation.run(payload);
    if (response) setResult(response);
  }

  async function copy() {
    if (!result) return;
    try {
      await navigator.clipboard.writeText(JSON.stringify(result, null, 2));
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      setCopied(false);
    }
  }

  return (
    <Page width="wide">
      <PageHeader
        title={spec.title}
        subtitle={spec.summary}
        meta={<Badge tone="brand">AI-assisted</Badge>}
      />
      <Split>
        <Card className={styles.formCard}>
          <form onSubmit={submit} noValidate aria-label={`${spec.title} inputs`}>
            {spec.note ? <p className={styles.noteLine}>{spec.note}</p> : null}
            <div className={styles.fields}>
              {spec.fields.map((field) => (
                <FieldControl
                  key={field.name}
                  field={field}
                  value={values[field.name]}
                  error={errors[field.name]}
                  onChange={(next) => {
                    setValues((current) => ({ ...current, [field.name]: next }));
                    if (errors[field.name]) setErrors((current) => ({ ...current, [field.name]: "" }));
                  }}
                />
              ))}
              <Button type="submit" variant="primary" loading={mutation.pending} icon={<Sparkles size={15} aria-hidden="true" />}>
                {mutation.pending ? "Analyzing…" : (spec.submitLabel ?? "Analyze")}
              </Button>
            </div>
          </form>
        </Card>

        <div aria-live="polite">
          {mutation.pending ? (
            <div className={styles.running} role="status">
              <Skeleton height={88} />
              <Skeleton height={180} />
              <p className={styles.runningText}>Running the analysis. This can take up to a minute.</p>
            </div>
          ) : mutation.error ? (
            <ErrorState error={mutation.error} title="The analysis could not be completed" />
          ) : result ? (
            <div className={styles.fields}>
              <div className={styles.resultHead}>
                <h2>Results</h2>
                <Button size="sm" onClick={copy} icon={<Copy size={14} aria-hidden="true" />}>
                  {copied ? "Copied" : "Copy as JSON"}
                </Button>
              </div>
              <ResultView result={result} />
            </div>
          ) : (
            <EmptyState
              title="Your results will appear here"
              description="Fill in the form and run the analysis. Results are saved to Analysis History."
            />
          )}
        </div>
      </Split>
      <Callout tone="info" title="How to use these results">
        Analyses are guidance generated from what you submit. Verify claims against your own analytics and search data before acting on them.
      </Callout>
    </Page>
  );
}
