"use client";

import { useState, type FormEvent } from "react";
import { Sparkles } from "lucide-react";
import { apiSend } from "@/app/lib/platform-api";
import { Button, Card, EmptyState, ErrorState, FieldSelect, FieldTextarea, Page, PageHeader, Skeleton, Split } from "../../_ui/kit";
import { OutputBlock } from "../../_ui/generator";
import { useTenant } from "../../_ui/use-resource";

const ACTIONS = [
  { value: "rephrase", label: "Rephrase" },
  { value: "shorten", label: "Shorten" },
  { value: "expand", label: "Expand" },
  { value: "casual", label: "Make it casual" },
  { value: "formal", label: "Make it formal" },
  { value: "generate", label: "Write variations" },
  { value: "repurpose", label: "Repurpose for a platform" },
];
const PLATFORMS = ["", "linkedin", "x", "instagram", "facebook", "tiktok"];
const TONES = ["professional", "friendly", "casual", "bold"];

type Reply = { result: string; provider: string; action: string };

export default function CopywriterPage() {
  const tenant = useTenant();
  const [text, setText] = useState("");
  const [action, setAction] = useState("rephrase");
  const [platform, setPlatform] = useState("");
  const [tone, setTone] = useState("professional");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<unknown>(null);
  const [reply, setReply] = useState<Reply | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!text.trim()) return setError("Paste or write some text first.");
    setError("");
    setBusy(true);
    setFailure(null);
    setReply(null);
    try {
      setReply(await apiSend<Reply>("/social/ai-assistant", "POST", { text: text.trim(), action, target_platform: platform || null, tone }, tenant));
    } catch (failed) {
      setFailure(failed);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Page width="wide">
      <PageHeader title="AI Copywriter" subtitle="Rewrite, shorten, expand or adapt a piece of copy. The AI model connected to your workspace does the writing." />
      <Split>
        <Card>
          <form onSubmit={submit} noValidate aria-label="Copy to rewrite" style={{ display: "grid", gap: 16 }}>
            <FieldTextarea label="Your copy" rows={8} value={text} maxLength={5000} error={error} onChange={(event) => setText(event.target.value)} hint={`${text.length.toLocaleString()} / 5,000`} />
            <FieldSelect label="What to do" value={action} onChange={(event) => setAction(event.target.value)}>{ACTIONS.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</FieldSelect>
            <FieldSelect label="Platform" value={platform} onChange={(event) => setPlatform(event.target.value)}>{PLATFORMS.map((item) => <option key={item} value={item}>{item ? item.charAt(0).toUpperCase() + item.slice(1) : "Any platform"}</option>)}</FieldSelect>
            <FieldSelect label="Tone" value={tone} onChange={(event) => setTone(event.target.value)}>{TONES.map((item) => <option key={item} value={item}>{item.charAt(0).toUpperCase() + item.slice(1)}</option>)}</FieldSelect>
            <Button type="submit" variant="primary" loading={busy} icon={<Sparkles size={15} aria-hidden="true" />}>{busy ? "Writing…" : "Rewrite"}</Button>
          </form>
        </Card>
        <div aria-live="polite">
          {busy ? <div style={{ display: "grid", gap: 12 }} role="status"><Skeleton height={140} /></div> : failure ? <ErrorState error={failure} title="Nothing was written" /> : reply ? (
            <Card><OutputBlock title="Result" text={reply.result} /><p style={{ margin: "14px 0 0", fontSize: 12.5, color: "var(--nx-muted)" }}>Written by {reply.provider}. Review before you use it.</p></Card>
          ) : <EmptyState title="Your rewrite will appear here" description="Add your copy and choose what to do with it." />}
        </div>
      </Split>
    </Page>
  );
}
