export type SimulatedAction =
  | "read"
  | "draft"
  | "update"
  | "publish"
  | "delete"
  | "change-access";
export type SimulatedDecision = "approved" | "denied";
export type AuditSensitivity =
  | "public"
  | "internal"
  | "customer"
  | "restricted";

export type AuditSimulationInput = {
  actor: string;
  action: SimulatedAction;
  resource: string;
  dataSensitivity: AuditSensitivity;
  decision: SimulatedDecision;
};

export type SimulatedAuditEvent = {
  id: string;
  timestamp: string;
  eventType: string;
  status: string;
  actor: string;
  action: SimulatedAction;
  resource: string;
  dataSensitivity: AuditSensitivity;
  approvalRequired: boolean;
  note: string;
};

export type AuditSimulation = {
  simulationOnly: true;
  approvalRequired: boolean;
  events: SimulatedAuditEvent[];
};

const ACTIONS_REQUIRING_APPROVAL = new Set<SimulatedAction>([
  "update",
  "publish",
  "delete",
  "change-access",
]);

export function requiresApproval(
  action: SimulatedAction,
  dataSensitivity: AuditSensitivity,
): boolean {
  return (
    ACTIONS_REQUIRING_APPROVAL.has(action) || dataSensitivity === "restricted"
  );
}

export function simulateAuditTrail(
  input: AuditSimulationInput,
  now = new Date(),
): AuditSimulation {
  const actor = input.actor.trim() || "Example agent";
  const resource = input.resource.trim() || "Example workspace record";
  const approvalRequired = requiresApproval(
    input.action,
    input.dataSensitivity,
  );
  const baseTime = now.getTime();

  const createEvent = (
    index: number,
    eventType: string,
    status: string,
    note: string,
  ): SimulatedAuditEvent => ({
    id: `sim-${baseTime.toString(36)}-${String(index + 1).padStart(2, "0")}`,
    timestamp: new Date(baseTime + index * 1000).toISOString(),
    eventType,
    status,
    actor,
    action: input.action,
    resource,
    dataSensitivity: input.dataSensitivity,
    approvalRequired,
    note,
  });

  if (!approvalRequired) {
    return {
      simulationOnly: true,
      approvalRequired: false,
      events: [
        createEvent(
          0,
          "agent.action.requested",
          "recorded",
          "The low-impact request is recorded in this illustrative scenario.",
        ),
        createEvent(
          1,
          "agent.action.completed",
          "completed",
          "The simulated action completed; no external system was contacted.",
        ),
      ],
    };
  }

  const approved = input.decision === "approved";
  return {
    simulationOnly: true,
    approvalRequired: true,
    events: [
      createEvent(
        0,
        "agent.action.proposed",
        "pending_approval",
        "The proposed action is held for explicit review.",
      ),
      createEvent(
        1,
        approved ? "agent.action.approved" : "agent.action.denied",
        approved ? "approved" : "denied",
        approved
          ? "A named reviewer approved this simulation."
          : "A reviewer denied this simulation; execution must not continue.",
      ),
      createEvent(
        2,
        approved ? "agent.action.executed" : "agent.action.blocked",
        approved ? "simulated_execution" : "not_executed",
        approved
          ? "Execution is shown for illustration only; no external system was contacted."
          : "No execution event was created after denial.",
      ),
    ],
  };
}
