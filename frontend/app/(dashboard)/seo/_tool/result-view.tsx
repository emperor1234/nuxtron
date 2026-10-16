"use client";

import type { ReactNode } from "react";
import {
  Badge,
  BulletList,
  Callout,
  Card,
  CardTitle,
  DataTable,
  Grid,
  Kpi,
  KpiGrid,
  KeyValue,
  Prose,
  ScoreRing,
  Stack,
  type Column,
} from "../../_ui/kit";
import styles from "./tool.module.css";

type Json = unknown;
type JsonObject = Record<string, Json>;

/** Bookkeeping the backend returns that is not part of the analysis itself. */
const HIDDEN = new Set([
  "analysis_id",
  "cached",
  "analysis_mode",
  "ai_available",
  "confidence_score",
  "fallback",
  "_enriched",
  "tenant_id",
  "status",
  "plan_id",
  "created_at",
  "generated_at",
  "analyzed_at",
  "audited_at",
  "rewritten_at",
]);

const ACRONYMS: Record<string, string> = {
  seo: "SEO", ai: "AI", aeo: "AEO", geo: "GEO", aio: "AIO", llm: "LLM", llmo: "LLMO", faq: "FAQ", paa: "PAA",
  url: "URL", urls: "URLs", kpi: "KPI", kpis: "KPIs", ctr: "CTR", ux: "UX", cx: "CX", sxo: "SXO", vso: "VSO",
  eeat: "E-E-A-T", ymyl: "YMYL", serp: "SERP", sge: "SGE", json: "JSON", ld: "LD", api: "API", rag: "RAG",
  gxo: "GXO", msvo: "MSVO", daeo: "DAEO", peao: "PEAO", cxao: "CXAO", sageo: "SAGEO", pct: "%", usd: "USD", id: "ID",
};

export function humanize(key: string): string {
  const words = key
    .replace(/^_+/, "")
    .split(/[_\s-]+/)
    .filter(Boolean)
    .map((word, index) => ACRONYMS[word.toLowerCase()] ?? (index === 0 ? word.charAt(0).toUpperCase() + word.slice(1) : word));
  return words.join(" ");
}

const isObject = (value: Json): value is JsonObject => typeof value === "object" && value !== null && !Array.isArray(value);
const isScalar = (value: Json): value is string | number | boolean | null =>
  value === null || ["string", "number", "boolean"].includes(typeof value);

function formatScalar(key: string, value: string | number | boolean | null): ReactNode {
  if (value === null || value === "") return <span className={styles.dash}>—</span>;
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value === "number") {
    if (/(probability|rate|ratio|index)$/.test(key) && value >= 0 && value <= 1) return `${Math.round(value * 100)}%`;
    if (/_pct$/.test(key)) return `${value}%`;
    return value.toLocaleString(undefined, { maximumFractionDigits: 2 });
  }
  return value;
}

/** One-line rendering for values that appear inside table cells and key/value rows. */
function inline(key: string, value: Json): ReactNode {
  if (isScalar(value)) return formatScalar(key, value);
  if (Array.isArray(value)) {
    if (value.length === 0) return <span className={styles.dash}>—</span>;
    if (value.every(isScalar)) return value.map((item) => String(item)).join(", ");
    return `${value.length} items`;
  }
  if (isObject(value)) {
    const parts = Object.entries(value)
      .filter(([, entry]) => isScalar(entry))
      .slice(0, 4)
      .map(([entryKey, entry]) => `${humanize(entryKey)}: ${String(formatScalar(entryKey, entry as never) ?? "")}`);
    return parts.length ? parts.join(" · ") : "—";
  }
  return String(value);
}

function SourceBanner({ result }: { result: JsonObject }) {
  const mode = result.analysis_mode;
  if (mode === "llm") {
    return (
      <Callout tone="info" title="Generated with an AI model">
        Treat this as guidance to review, not as a measurement from search engines.
      </Callout>
    );
  }
  if (mode === "heuristic" || result.ai_available === false) {
    return (
      <Callout tone="warning" title="Rule-based guidance — no AI model was used">
        Scores are indicators computed from what you submitted. They are not measurements from search engines or third-party data.
      </Callout>
    );
  }
  return null;
}

function Records({ title, rows }: { title: string; rows: JsonObject[] }) {
  const keys: string[] = [];
  for (const row of rows) {
    for (const [key, value] of Object.entries(row)) {
      if (keys.includes(key)) continue;
      const simple = isScalar(value) || (Array.isArray(value) && value.every(isScalar)) || isObject(value);
      if (simple) keys.push(key);
    }
  }
  const columns: Column<JsonObject>[] = keys.slice(0, 6).map((key, index) => ({
    key,
    header: humanize(key),
    render: (row) => <span className={styles.cell}>{inline(key, row[key])}</span>,
    strong: index === 0,
    numeric: rows.every((row) => typeof row[key] === "number"),
  }));
  return (
    <Card pad={false}>
      <div className={styles.tableTitle}>
        <h3>{title}</h3>
        <Badge>{rows.length}</Badge>
      </div>
      <DataTable columns={columns} rows={rows} getKey={(_, index) => index} caption={title} dense />
    </Card>
  );
}

function Section({ name, value, depth }: { name: string; value: Json; depth: number }) {
  const title = humanize(name);

  if (typeof value === "string") {
    return (
      <Card>
        <CardTitle>{title}</CardTitle>
        <Prose>{value}</Prose>
      </Card>
    );
  }

  if (Array.isArray(value)) {
    if (value.length === 0) return null;
    if (value.every((item) => typeof item === "string")) {
      return (
        <Card>
          <CardTitle>{title}</CardTitle>
          <BulletList items={value as string[]} />
        </Card>
      );
    }
    if (value.every(isObject)) return <Records title={title} rows={value as JsonObject[]} />;
    return (
      <Card>
        <CardTitle>{title}</CardTitle>
        <BulletList items={value.map((item) => inline(name, item))} />
      </Card>
    );
  }

  if (isObject(value)) {
    const entries = Object.entries(value).filter(([key]) => !HIDDEN.has(key));
    if (entries.length === 0) return null;
    const scalars = entries.filter(([, entry]) => isScalar(entry) && entry !== "");
    const longText = scalars.filter(([, entry]) => typeof entry === "string" && entry.length > 120);
    const short = scalars.filter(([key]) => !longText.some(([longKey]) => longKey === key));
    const nested = entries.filter(([, entry]) => !isScalar(entry));
    return (
      <Card>
        <CardTitle>{title}</CardTitle>
        <Stack>
          {short.length > 0 ? (
            <KeyValue items={short.map(([key, entry]) => ({ label: humanize(key), value: formatScalar(key, entry as never) }))} />
          ) : null}
          {longText.map(([key, entry]) => (
            <div key={key}>
              <p className={styles.miniTitle}>{humanize(key)}</p>
              <Prose>{String(entry)}</Prose>
            </div>
          ))}
          {depth < 2
            ? nested.map(([key, entry]) => (
                <div key={key}>
                  <p className={styles.miniTitle}>{humanize(key)}</p>
                  <Nested value={entry} name={key} />
                </div>
              ))
            : null}
        </Stack>
      </Card>
    );
  }

  return null;
}

/** Compact rendering for values nested inside an object card. */
function Nested({ name, value }: { name: string; value: Json }) {
  if (Array.isArray(value)) {
    if (value.length === 0) return <span className={styles.dash}>—</span>;
    if (value.every(isScalar)) return <BulletList items={value.map((item) => String(item))} />;
    if (value.every(isObject)) {
      return (
        <ul className={styles.records}>
          {(value as JsonObject[]).map((row, index) => (
            <li key={index}>{inline(name, row)}</li>
          ))}
        </ul>
      );
    }
  }
  if (isObject(value)) {
    return (
      <KeyValue
        items={Object.entries(value).map(([key, entry]) => ({ label: humanize(key), value: inline(key, entry) }))}
      />
    );
  }
  return <>{inline(name, value)}</>;
}

/**
 * Renders any analysis response from the SEO platform: score rings first,
 * then headline numbers, quick wins, and every remaining field as the most
 * natural component for its shape. Nothing is invented — only what the API
 * returned is shown.
 */
export function ResultView({ result }: { result: JsonObject }) {
  const entries = Object.entries(result).filter(([key]) => !HIDDEN.has(key));
  const scores = entries.filter(([key, value]) => key.endsWith("_score") && typeof value === "number" && value >= 0 && value <= 100) as Array<[string, number]>;
  const scoreKeys = new Set(scores.map(([key]) => key));
  const numbers = entries.filter(([key, value]) => typeof value === "number" && !scoreKeys.has(key)) as Array<[string, number]>;
  const numberKeys = new Set(numbers.map(([key]) => key));
  const quickWins = result.quick_wins;
  const rest = entries.filter(([key]) => !scoreKeys.has(key) && !numberKeys.has(key) && key !== "quick_wins");

  const shortStrings = rest.filter(([, value]) => typeof value === "string" && value.length <= 120 && value !== "");
  const shortKeys = new Set(shortStrings.map(([key]) => key));
  const sections = rest.filter(([key, value]) => !shortKeys.has(key) && !(typeof value === "boolean"));
  const booleans = rest.filter(([, value]) => typeof value === "boolean") as Array<[string, boolean]>;

  return (
    <Stack>
      <SourceBanner result={result} />

      {scores.length > 0 ? (
        <Grid cols={4}>
          {scores.map(([key, value]) => (
            <Card key={key} className={styles.scoreCard}>
              <ScoreRing value={value} label={humanize(key)} />
              <span className={styles.scoreLabel}>{humanize(key.replace(/_score$/, ""))}</span>
            </Card>
          ))}
        </Grid>
      ) : null}

      {numbers.length > 0 ? (
        <KpiGrid>
          {numbers.map(([key, value]) => (
            <Kpi key={key} label={humanize(key)} value={formatScalar(key, value)} />
          ))}
        </KpiGrid>
      ) : null}

      {shortStrings.length > 0 || booleans.length > 0 ? (
        <Card>
          <KeyValue
            items={[
              ...shortStrings.map(([key, value]) => ({ label: humanize(key), value: String(value) })),
              ...booleans.map(([key, value]) => ({ label: humanize(key), value: value ? "Yes" : "No" })),
            ]}
          />
        </Card>
      ) : null}

      {Array.isArray(quickWins) && quickWins.length > 0 ? (
        <Card className={styles.quickWins}>
          <CardTitle sub="Highest-leverage changes to make first.">Quick wins</CardTitle>
          <BulletList items={quickWins.map((item) => inline("quick_wins", item))} />
        </Card>
      ) : null}

      {sections.map(([key, value]) => (
        <Section key={key} name={key} value={value} depth={0} />
      ))}
    </Stack>
  );
}
