import type { Metadata } from "next";
import { FreeToolFrame } from "../_components/free-tool-frame";
import { AgentPermissionMatrix } from "../_components/agent-permission-matrix";

export const metadata: Metadata = {
  title: "Agent permission matrix | Free tools | Nuxtron",
  description:
    "Generate a least-privilege AI agent permission matrix with clear data scopes, human approval points, and audit evidence.",
  alternates: { canonical: "/tools/agent-permission-matrix" },
};

export default function AgentPermissionMatrixPage() {
  return (
    <FreeToolFrame
      eyebrow="Free agent-governance utility"
      title="Agent permission matrix"
      description="Turn a proposed agent workflow into a practical starting matrix for data scope, action grants, approval, and audit evidence."
    >
      <AgentPermissionMatrix />
    </FreeToolFrame>
  );
}
