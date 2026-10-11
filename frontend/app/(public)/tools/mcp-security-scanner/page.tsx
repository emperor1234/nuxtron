import type { Metadata } from "next";
import { FreeToolFrame } from "../_components/free-tool-frame";
import { McpSecurityScanner } from "../_components/mcp-security-scanner";

export const metadata: Metadata = {
  title: "MCP security scanner | Free tools | Nuxtron",
  description:
    "Review an MCP server configuration locally for risky commands, broad access, insecure remote endpoints, and inline credentials.",
  alternates: { canonical: "/tools/mcp-security-scanner" },
};

export default function McpSecurityScannerPage() {
  return (
    <FreeToolFrame
      eyebrow="Free security utility"
      title="MCP security scanner"
      description="Review a pasted MCP client configuration for common static risk patterns. The scanner never sends the JSON to a server."
    >
      <McpSecurityScanner />
    </FreeToolFrame>
  );
}
