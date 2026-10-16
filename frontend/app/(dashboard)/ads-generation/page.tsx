"use client";

import { useState, type FormEvent } from "react";
import { Sparkles } from "lucide-react";
import { apiSend } from "@/app/lib/platform-api";
import { Badge, BulletList, Button, Callout, Card, EmptyState, ErrorState, Field, FieldSelect, Page, PageHeader, Skeleton, Split } from "../_ui/kit";
import { CopyButton, OutputBlock } from "../_ui/generator";
import { useTenant } from "../_ui/use-resource";

const PLATFORMS = [
  { value: "google", label: "Google" },
  { value: "meta", label: "Meta" },
  { value: "linkedin", label: "LinkedIn" },
  { value: "tiktok", label: "TikTok" },
  { value: "instagram", label: "Instagram" },
  { value: "youtube", label: "YouTube" },
  { value: "facebook", label: "Facebook" },
  { value: "x", label: "X" },
  { value: "threads", label: "Threads" },
  { value: "snapchat", label: "Snapchat" },
];
const OBJECTIVES = ["traffic", "leads", "sales", "awareness"];

type AdResult = {
  platform: string;
  objective: string;
  headlines: string[];
  descriptions: string[];
  cta?: string;
  provider_used?: string;
  model_used?: string;
  outputs?: { text?: string };
};

export default function AdCreativePage() {
  const tenant = useTenant();
  const [product, setProduct] = useState("");
  const [audience, setAudience] = useState("");
  const [platform, setPlatform] = useState("meta");
  const [objective, setObjective] = useState("traffic");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<unknown>(null);
  const [result, setResult] = useState<AdResult | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    const found: Record<string, string> = {};
    if (product.trim().length < 2) found.product = "Name the product or offer.";
    if (audience.trim().length < 2) found.audience = "Say who the ad is for.";
    setErrors(found);
    if (Object.keys(found).length) return;
    setBusy(true);
    setFailure(null);
    setResult(null);
    try {
      setResult(await apiSend<AdResult>("/ads/generate", "POST", { product: product.trim(), audience: audience.trim(), platform, objective }, tenant));
    } catch (error) {
      setFailure(error);
    } finally {
      setBusy(false);
    }
  }

  const all = result ? [...result.headlines, ...result.descriptions, ...(result.outputs?.text ? [result.outputs.text] : [])].join("\n") : "";

  return (
    <Page width="wide">
      <PageHeader title="Paid Ad Creative" subtitle="Write ad headlines and descriptions for a platform and objective. Output comes from the AI model connected to your workspace." />
      <Split>
        <Card>
          <form onSubmit={submit} noValidate aria-label="Ad details" style={{ display: "grid", gap: 16 }}>
            <Field label="Product or offer" value={product} error={errors.product} maxLength={140} onChange={(event) => setProduct(event.target.value)} />
            <Field label="Audience" value={audience} error={errors.audience} maxLength={120} onChange={(event) => setAudience(event.target.value)} />
            <FieldSelect label="Platform" value={platform} onChange={(event) => setPlatform(event.target.value)}>{PLATFORMS.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</FieldSelect>
            <FieldSelect label="Objective" value={objective} onChange={(event) => setObjective(event.target.value)}>{OBJECTIVES.map((item) => <option key={item} value={item}>{item.charAt(0).toUpperCase() + item.slice(1)}</option>)}</FieldSelect>
            <Button type="submit" variant="primary" loading={busy} icon={<Sparkles size={15} aria-hidden="true" />}>{busy ? "Writing…" : "Generate ads"}</Button>
          </form>
        </Card>
        <div aria-live="polite">
          {busy ? (
            <div style={{ display: "grid", gap: 12 }} role="status"><Skeleton height={64} /><Skeleton height={160} /></div>
          ) : failure ? (
            <ErrorState error={failure} title="No ad copy was generated" />
          ) : result ? (
            <Card>
              <div style={{ display: "grid", gap: 20 }}>
                <OutputBlock title="Headlines"><BulletList items={result.headlines} /></OutputBlock>
                <OutputBlock title="Descriptions"><BulletList items={result.descriptions} /></OutputBlock>
                {result.cta ? <OutputBlock title="Call to action"><Badge tone="brand">{result.cta}</Badge></OutputBlock> : null}
                {result.outputs?.text ? <OutputBlock title="Full copy" text={result.outputs.text} /> : null}
                <p style={{ margin: 0, fontSize: 12.5, color: "var(--nx-muted)" }}>Written by {result.provider_used ?? "the connected model"}{result.model_used ? ` (${result.model_used})` : ""}. Check each platform&apos;s ad policies before you run it.</p>
                <div><CopyButton text={all} label="Copy everything" /></div>
              </div>
            </Card>
          ) : (
            <EmptyState title="Your ad copy will appear here" description="Describe the product and audience, then generate." />
          )}
        </div>
      </Split>
      <Callout tone="info">Nuxtron writes the copy. Creating and launching campaigns happens in the ad platform itself.</Callout>
    </Page>
  );
}
