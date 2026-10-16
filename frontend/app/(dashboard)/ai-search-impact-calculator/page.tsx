"use client";

import { useState, type FormEvent } from "react";
import { apiSend } from "@/app/lib/platform-api";
import { Button, Callout, Card, ErrorState, Field, Kpi, KpiGrid, Page, PageHeader, Section, Split, Tabs } from "../_ui/kit";
import { useTenant } from "../_ui/use-resource";

type Spec = { key: string; label: string; initial: string; max?: number; hint?: string };
type Calc = { endpoint: string; title: string; fields: Spec[] };

const CALCS: Record<string, Calc> = {
  impact: {
    endpoint: "/search-everywhere/ai-search-impact-calculator",
    title: "AI search impact",
    fields: [
      { key: "monthly_sessions", label: "Monthly site sessions", initial: "100000" },
      { key: "current_ai_visibility_pct", label: "Share of AI answers that mention you now (%)", initial: "1", max: 100 },
      { key: "target_ai_visibility_pct", label: "Share you aim for (%)", initial: "12", max: 100 },
      { key: "ai_ctr_pct", label: "Click-through from AI answers (%)", initial: "18", max: 100, hint: "Use your own data if you have it." },
      { key: "conversion_rate_pct", label: "Visit-to-sale rate (%)", initial: "2.2", max: 100 },
      { key: "avg_order_value_usd", label: "Average order value (USD)", initial: "120" },
      { key: "gross_margin_pct", label: "Gross margin (%)", initial: "65", max: 100 },
    ],
  },
  savings: {
    endpoint: "/search-everywhere/cost-savings-calculator",
    title: "Automation savings",
    fields: [
      { key: "sites_count", label: "Sites", initial: "10" },
      { key: "pages_per_site", label: "Pages per site", initial: "500" },
      { key: "monthly_deployments", label: "Deployments per month", initial: "4" },
      { key: "manual_minutes_per_page", label: "Manual minutes per page", initial: "1.5" },
      { key: "hourly_rate_usd", label: "Hourly cost of the work (USD)", initial: "80" },
      { key: "automation_coverage_pct", label: "Work you expect to automate (%)", initial: "85", max: 100 },
      { key: "tool_monthly_cost_usd", label: "Tool cost per month (USD)", initial: "399" },
    ],
  },
};

const label = (key: string) => key.replace(/_usd$/, "").replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase());
function show(key: string, value: number): string {
  if (key.endsWith("_usd")) return value.toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });
  return value.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

function Calculator({ calc }: { calc: Calc }) {
  const tenant = useTenant();
  const [values, setValues] = useState<Record<string, string>>(() => Object.fromEntries(calc.fields.map((field) => [field.key, field.initial])));
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<unknown>(null);
  const [output, setOutput] = useState<Record<string, number> | null>(null);

  async function run(event: FormEvent) {
    event.preventDefault();
    const found: Record<string, string> = {};
    for (const field of calc.fields) {
      const n = Number(values[field.key]);
      if (values[field.key].trim() === "" || Number.isNaN(n) || n < 0 || (field.max !== undefined && n > field.max)) found[field.key] = field.max ? `Enter a number from 0 to ${field.max}.` : "Enter a number of zero or more.";
    }
    setErrors(found);
    if (Object.keys(found).length) return;
    setBusy(true);
    setFailure(null);
    try {
      const body = Object.fromEntries(calc.fields.map((field) => [field.key, Number(values[field.key])]));
      setOutput((await apiSend<{ output: Record<string, number> }>(calc.endpoint, "POST", body, tenant)).output);
    } catch (caught) {
      setFailure(caught);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Split>
      <Card>
        <form onSubmit={run} noValidate aria-label={calc.title} style={{ display: "grid", gap: 16 }}>
          {calc.fields.map((field) => (
            <Field key={field.key} label={field.label} inputMode="decimal" value={values[field.key]} error={errors[field.key]} hint={field.hint} onChange={(event) => setValues({ ...values, [field.key]: event.target.value })} />
          ))}
          <Button type="submit" variant="primary" loading={busy}>Calculate</Button>
        </form>
      </Card>
      <div aria-live="polite" style={{ display: "grid", gap: 16, alignContent: "start" }}>
        {failure ? <ErrorState error={failure} title="Could not calculate" /> : null}
        {output ? (
          <Section title="Result">
            <KpiGrid>{Object.entries(output).map(([key, value]) => <Kpi key={key} label={label(key)} value={show(key, value)} />)}</KpiGrid>
          </Section>
        ) : <Callout tone="info">The numbers shown are starting assumptions. Replace them with your own, then calculate.</Callout>}
        <Callout tone="info">This is arithmetic on the numbers you enter. It is a projection, not a forecast.</Callout>
      </div>
    </Split>
  );
}

export default function AiSearchImpactPage() {
  const [tab, setTab] = useState("impact");
  return (
    <Page width="wide">
      <PageHeader title="Impact Calculators" subtitle="Turn your own assumptions into a clear estimate." tabs={<Tabs items={[{ id: "impact", label: "AI search impact" }, { id: "savings", label: "Automation savings" }]} value={tab} onChange={setTab} label="Calculators" />} />
      <Calculator key={tab} calc={CALCS[tab]} />
    </Page>
  );
}
