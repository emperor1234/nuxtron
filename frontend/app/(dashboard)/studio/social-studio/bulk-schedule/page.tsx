"use client";

import { useMemo, useRef, useState } from "react";
import { Upload } from "lucide-react";
import { apiGet, apiSend } from "@/app/lib/platform-api";
import {
  Badge,
  Button,
  ButtonLink,
  Callout,
  Card,
  CardTitle,
  DataTable,
  EmptyState,
  FieldTextarea,
  Kpi,
  KpiGrid,
  Page,
  PageHeader,
  Section,
  type Column,
} from "../../../_ui/kit";
import { formatDateTime, truncate } from "../../../_ui/format";
import { ResourceView, useResource, useTenant } from "../../../_ui/use-resource";

type Template = { template_fields: string[]; example_row: Record<string, string>; supported_networks: string[]; max_rows: number };
type Job = { id: number; total_rows: number; created: number; errors: number; status: string; created_at: string };
type Loaded = { template: Template; jobs: Job[] };

type Row = {
  line: number;
  values: Record<string, string>;
  problems: string[];
};

type SubmitResult = { created: Array<{ row: number; post_id: number }>; errors: Array<{ row: number; error: string }> };

/** Minimal RFC 4180 parser: quoted fields, escaped quotes, commas and newlines inside quotes. */
function parseCsv(input: string): string[][] {
  const rows: string[][] = [];
  let field = "";
  let row: string[] = [];
  let quoted = false;
  for (let index = 0; index < input.length; index += 1) {
    const char = input[index];
    if (quoted) {
      if (char === '"' && input[index + 1] === '"') {
        field += '"';
        index += 1;
      } else if (char === '"') {
        quoted = false;
      } else {
        field += char;
      }
    } else if (char === '"') {
      quoted = true;
    } else if (char === ",") {
      row.push(field);
      field = "";
    } else if (char === "\n" || char === "\r") {
      if (char === "\r" && input[index + 1] === "\n") index += 1;
      row.push(field);
      if (row.some((cell) => cell.trim() !== "")) rows.push(row);
      row = [];
      field = "";
    } else {
      field += char;
    }
  }
  row.push(field);
  if (row.some((cell) => cell.trim() !== "")) rows.push(row);
  return rows;
}

function validate(values: Record<string, string>, networks: Set<string>): string[] {
  const problems: string[] = [];
  const platform = (values.platform ?? "").trim().toLowerCase();
  if (!platform) problems.push("Missing platform");
  else if (!networks.has(platform)) problems.push(`Unsupported platform “${platform}”`);
  const text = (values.text ?? "").trim();
  if (!text) problems.push("Missing text");
  else if (text.length > 4000) problems.push("Text is over 4,000 characters");
  const when = (values.publish_at ?? "").trim();
  if (!when) problems.push("Missing publish_at");
  else if (Number.isNaN(new Date(when).getTime())) problems.push("publish_at is not a valid date and time");
  return problems;
}

export default function BulkImportPage() {
  const tenant = useTenant();
  const resource = useResource<Loaded>(async (id) => {
    const [template, jobs] = await Promise.all([
      apiGet<Template>("/social/bulk-schedule/template", id),
      apiGet<{ jobs?: Job[] }>("/social/bulk-schedule/jobs", id),
    ]);
    return { template, jobs: jobs.jobs ?? [] };
  });

  const fileInput = useRef<HTMLInputElement>(null);
  const [text, setText] = useState("");
  const [fileName, setFileName] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<SubmitResult | null>(null);

  const networks = useMemo(() => new Set(resource.data?.template.supported_networks ?? []), [resource.data]);
  const maxRows = resource.data?.template.max_rows ?? 500;

  const parsed = useMemo(() => {
    if (!text.trim()) return { rows: [] as Row[], headerError: null as string | null };
    const table = parseCsv(text);
    const header = (table[0] ?? []).map((cell) => cell.trim().toLowerCase());
    const missing = ["platform", "text", "publish_at"].filter((name) => !header.includes(name));
    if (missing.length) return { rows: [], headerError: `The first row must be a header including: ${missing.join(", ")}.` };
    const rows = table.slice(1).map((cells, index): Row => {
      const values: Record<string, string> = {};
      header.forEach((name, column) => {
        values[name] = (cells[column] ?? "").trim();
      });
      return { line: index + 2, values, problems: validate(values, networks) };
    });
    return { rows, headerError: rows.length > maxRows ? `At most ${maxRows} rows per import.` : null };
  }, [text, networks, maxRows]);

  const valid = parsed.rows.filter((row) => row.problems.length === 0);
  const invalid = parsed.rows.length - valid.length;

  async function onFile(file: File | undefined) {
    if (!file) return;
    if (file.size > 1_000_000) return setError("Choose a CSV smaller than 1 MB.");
    setError(null);
    setResult(null);
    setFileName(file.name);
    setText(await file.text());
  }

  async function submit() {
    setSubmitting(true);
    setError(null);
    try {
      const payload = valid.map((row) => ({
        platform: row.values.platform.toLowerCase(),
        text: row.values.text,
        publish_at: new Date(row.values.publish_at).toISOString(),
        hashtags: row.values.hashtags ?? "",
        media_urls: row.values.media_urls ?? "",
      }));
      const response = await apiSend<SubmitResult>("/social/bulk-schedule", "POST", { posts: payload }, tenant);
      setResult(response);
      setText("");
      setFileName("");
      await resource.reload();
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "The import failed.");
    } finally {
      setSubmitting(false);
    }
  }

  const previewColumns: Column<Row>[] = [
    { key: "line", header: "Row", numeric: true, render: (row) => row.line },
    { key: "platform", header: "Platform", render: (row) => row.values.platform },
    { key: "text", header: "Text", render: (row) => truncate(row.values.text ?? "", 80) },
    { key: "publish_at", header: "Planned for", render: (row) => row.values.publish_at },
    {
      key: "state",
      header: "Check",
      render: (row) =>
        row.problems.length === 0 ? <Badge tone="success">Ready</Badge> : <Badge tone="danger">{row.problems.join("; ")}</Badge>,
    },
  ];

  const jobColumns: Column<Job>[] = [
    { key: "when", header: "Imported", render: (job) => formatDateTime(job.created_at) },
    { key: "rows", header: "Rows", numeric: true, render: (job) => job.total_rows },
    { key: "created", header: "Added", numeric: true, render: (job) => job.created },
    { key: "errors", header: "Rejected", numeric: true, render: (job) => job.errors },
  ];

  return (
    <Page>
      <PageHeader
        title="Bulk Import"
        subtitle="Plan many posts at once from a CSV. Rows are checked here first, and only valid rows are added to your plan."
        actions={<ButtonLink href="/studio/social-studio/queue">View queue</ButtonLink>}
      />
      <ResourceView resource={resource}>
        {(data) => (
          <>
            <Card>
              <CardTitle sub={`Columns: ${data.template.template_fields.join(", ")}. Required: platform, text, publish_at (ISO 8601, e.g. ${data.template.example_row.publish_at}).`}>
                1. Add your CSV
              </CardTitle>
              <div style={{ display: "grid", gap: 14 }}>
                <input ref={fileInput} type="file" accept=".csv,text/csv" hidden onChange={(event) => void onFile(event.target.files?.[0])} />
                <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
                  <Button icon={<Upload size={15} aria-hidden="true" />} onClick={() => fileInput.current?.click()}>
                    Choose a CSV
                  </Button>
                  {fileName ? <Badge>{fileName}</Badge> : null}
                  <Button
                    variant="quiet"
                    onClick={() => {
                      setText(`${data.template.template_fields.join(",")}\n${data.template.template_fields.map((field) => JSON.stringify(data.template.example_row[field] ?? "")).join(",")}`);
                      setFileName("");
                      setResult(null);
                    }}
                  >
                    Use the example row
                  </Button>
                </div>
                <FieldTextarea
                  label="Or paste CSV"
                  rows={6}
                  value={text}
                  onChange={(event) => {
                    setText(event.target.value);
                    setResult(null);
                  }}
                  placeholder={data.template.template_fields.join(",")}
                />
              </div>
            </Card>

            {error ? <Callout tone="danger">{error}</Callout> : null}
            {parsed.headerError ? <Callout tone="danger">{parsed.headerError}</Callout> : null}

            {parsed.rows.length > 0 && !parsed.headerError ? (
              <Section
                title="2. Review"
                description="Fix any rejected rows in your file and re-add it, or import only the rows that are ready."
                actions={
                  <Button variant="primary" loading={submitting} disabled={valid.length === 0} onClick={() => void submit()}>
                    Add {valid.length} post{valid.length === 1 ? "" : "s"} to the plan
                  </Button>
                }
              >
                <KpiGrid>
                  <Kpi label="Rows" value={parsed.rows.length} />
                  <Kpi label="Ready" value={valid.length} />
                  <Kpi label="Need fixing" value={invalid} />
                </KpiGrid>
                <DataTable columns={previewColumns} rows={parsed.rows} getKey={(row) => row.line} caption="Rows to import" pageSize={10} dense />
              </Section>
            ) : null}

            {result ? (
              <Callout tone={result.errors.length ? "warning" : "success"} title={`Added ${result.created.length} post${result.created.length === 1 ? "" : "s"} to your plan`}>
                {result.errors.length ? `${result.errors.length} row(s) were rejected by the server: ${result.errors.map((item) => `row ${item.row}: ${item.error}`).join("; ")}` : "Every row was accepted."}
              </Callout>
            ) : null}

            <Section title="Previous imports">
              {data.jobs.length === 0 ? (
                <EmptyState title="No imports yet" description="Imports you run will be listed here." />
              ) : (
                <DataTable columns={jobColumns} rows={data.jobs} getKey={(job) => job.id} caption="Previous imports" dense />
              )}
            </Section>
          </>
        )}
      </ResourceView>
    </Page>
  );
}
