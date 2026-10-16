"use client";

import { useRef, useState } from "react";
import { Upload } from "lucide-react";
import { apiSend } from "@/app/lib/platform-api";
import { Button, Callout, Card, EmptyState, ErrorState, FieldSelect, Page, PageHeader, Split, Tabs } from "../../_ui/kit";
import { useTenant } from "../../_ui/use-resource";

type Operation = "upscale" | "neural-filter";
type EditResponse = { image_url?: string; metadata?: { width?: number; height?: number } };

const FILTERS = [
  { value: "clarity", label: "Clarity (sharpen)" },
  { value: "cinematic", label: "Cinematic" },
  { value: "vivid", label: "Vivid" },
  { value: "mono", label: "Black and white" },
  { value: "glow", label: "Soft glow" },
];
const MAX_BYTES = 8 * 1024 * 1024;

function readAsDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result ?? ""));
    reader.onerror = () => reject(new Error("The file could not be read."));
    reader.readAsDataURL(file);
  });
}

export default function ImageStudioPage() {
  const tenant = useTenant();
  const input = useRef<HTMLInputElement>(null);
  const [operation, setOperation] = useState<Operation>("upscale");
  const [source, setSource] = useState("");
  const [name, setName] = useState("");
  const [factor, setFactor] = useState("2");
  const [filter, setFilter] = useState("clarity");
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const [failure, setFailure] = useState<unknown>(null);
  const [result, setResult] = useState<EditResponse | null>(null);


  async function choose(file: File | undefined) {
    if (!file) return;
    setProblem(null);
    if (!file.type.startsWith("image/")) return setProblem("Choose an image file (PNG, JPEG or WebP).");
    if (file.size > MAX_BYTES) return setProblem("Choose an image smaller than 8 MB.");
    setSource(await readAsDataUrl(file));
    setName(file.name);
    setResult(null);
    setFailure(null);
  }

  async function run() {
    setBusy(true);
    setFailure(null);
    setResult(null);
    try {
      const path = operation === "upscale" ? "/ai/image/upscale" : "/ai/image/neural-filter";
      const body = operation === "upscale" ? { image_data: source, upscale_factor: Number(factor) } : { image_data: source, filter_name: filter };
      setResult(await apiSend<EditResponse>(path, "POST", body, tenant));
    } catch (error) {
      setFailure(error);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Page width="wide">
      <PageHeader title="Image Studio" subtitle="Upscale and sharpen an image, or apply a filter. Edits run on Nuxtron's servers; nothing is sent to a third-party model." />
      <Tabs items={[{ id: "upscale", label: "Upscale" }, { id: "neural-filter", label: "Filters" }]} value={operation} onChange={(id) => { setOperation(id as Operation); setResult(null); setFailure(null); }} label="Edit type" />
      <Split>
        <Card>
          <div style={{ display: "grid", gap: 16 }}>
            <input ref={input} type="file" accept="image/*" hidden onChange={(event) => void choose(event.target.files?.[0])} />
            <Button icon={<Upload size={15} aria-hidden="true" />} onClick={() => input.current?.click()}>{name ? "Choose a different image" : "Choose an image"}</Button>
            {name ? <p style={{ margin: 0, fontSize: 13, color: "var(--nx-muted)" }}>{name}</p> : null}
            {problem ? <Callout tone="danger">{problem}</Callout> : null}
            {operation === "upscale" ? (
              <FieldSelect label="Enlarge by" value={factor} onChange={(event) => setFactor(event.target.value)}>
                {["2", "3", "4"].map((value) => <option key={value} value={value}>{value}×</option>)}
              </FieldSelect>
            ) : (
              <FieldSelect label="Filter" value={filter} onChange={(event) => setFilter(event.target.value)}>
                {FILTERS.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
              </FieldSelect>
            )}
            <Button variant="primary" loading={busy} disabled={!source} onClick={() => void run()}>{operation === "upscale" ? "Upscale" : "Apply filter"}</Button>
          </div>
        </Card>
        <div aria-live="polite" style={{ display: "grid", gap: 16 }}>
          {failure ? <ErrorState error={failure} title="The image could not be processed" /> : null}
          {!source && !result ? <EmptyState title="Choose an image to begin" description="PNG, JPEG or WebP up to 8 MB." /> : null}
          {source ? (
            <Card>
              <p style={{ margin: "0 0 8px", fontSize: 12, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.04em", color: "var(--nx-muted)" }}>Original</p>
              <img src={source} alt="Original upload" style={{ maxWidth: "100%", borderRadius: 8 }} />
            </Card>
          ) : null}
          {result?.image_url ? (
            <Card>
              <p style={{ margin: "0 0 8px", fontSize: 12, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.04em", color: "var(--nx-muted)" }}>
                Result{result.metadata?.width ? ` · ${result.metadata.width}×${result.metadata.height}` : ""}
              </p>
              <img src={result.image_url} alt="Edited result" style={{ maxWidth: "100%", borderRadius: 8 }} />
              <div style={{ marginTop: 12 }}>
                <a href={result.image_url} download={`edited-${name || "image"}.png`}>Download</a>
              </div>
            </Card>
          ) : null}
        </div>
      </Split>
    </Page>
  );
}
