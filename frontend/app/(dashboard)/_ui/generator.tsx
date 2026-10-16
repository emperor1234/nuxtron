"use client";

import { useState, type ReactNode } from "react";
import { Copy } from "lucide-react";
import { Button } from "./kit";

/** Copy-to-clipboard button for generated text. Reports failure instead of pretending it worked. */
export function CopyButton({ text, label = "Copy" }: { text: string; label?: string }) {
  const [state, setState] = useState<"idle" | "copied" | "failed">("idle");
  async function copy() {
    try {
      await navigator.clipboard.writeText(text);
      setState("copied");
    } catch {
      setState("failed");
    }
    setTimeout(() => setState("idle"), 1800);
  }
  return (
    <Button size="sm" onClick={() => void copy()} icon={<Copy size={14} aria-hidden="true" />}>
      {state === "copied" ? "Copied" : state === "failed" ? "Copy failed" : label}
    </Button>
  );
}

/** Labelled block of generated output. */
export function OutputBlock({ title, text, children }: { title: string; text?: string; children?: ReactNode }) {
  return (
    <div style={{ display: "grid", gap: 8 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12 }}>
        <h3 style={{ margin: 0, fontSize: 13, fontWeight: 700, letterSpacing: "0.04em", textTransform: "uppercase", color: "var(--nx-muted)" }}>{title}</h3>
        {text ? <CopyButton text={text} /> : null}
      </div>
      {text ? <div style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere", lineHeight: 1.65, fontSize: 14.5 }}>{text}</div> : null}
      {children}
    </div>
  );
}
