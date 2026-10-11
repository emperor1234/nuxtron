import type { Metadata } from "next";
import { FreeToolFrame } from "../_components/free-tool-frame";
import { AgentAuditLogSimulator } from "../_components/agent-audit-log-simulator";

export const metadata: Metadata = {
  title: "Agent audit-log simulator | Free tools | Nuxtron",
  description:
    "Simulate an AI agent approval, denial, or completion trail. No real systems or records are touched.",
  alternates: { canonical: "/tools/agent-audit-log-simulator" },
};

export default function AgentAuditLogSimulatorPage() {
  return (
    <FreeToolFrame
      eyebrow="Free agent-governance utility"
      title="Agent audit-log simulator"
      description="Explore what a governed agent action can record before approval, after denial, and upon completion. Every event shown here is illustrative only."
    >
      <AgentAuditLogSimulator />
    </FreeToolFrame>
  );
}
