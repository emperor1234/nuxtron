import { describe, expect, it } from "vitest";
import { simulateAuditTrail } from "./audit-simulator";

const timestamp = new Date("2026-01-02T03:04:05.000Z");

describe("agent audit-log simulator", () => {
  it("records proposal, approval, and a simulated execution when approved", () => {
    const simulation = simulateAuditTrail(
      {
        actor: "Content agent",
        action: "publish",
        resource: "campaign draft",
        dataSensitivity: "internal",
        decision: "approved",
      },
      timestamp,
    );
    expect(simulation.simulationOnly).toBe(true);
    expect(simulation.approvalRequired).toBe(true);
    expect(simulation.events.map((event) => event.status)).toEqual([
      "pending_approval",
      "approved",
      "simulated_execution",
    ]);
    expect(simulation.events[2].note).toContain("no external system");
  });

  it("never creates an execution event after a denied approval", () => {
    const simulation = simulateAuditTrail(
      {
        actor: "Agent",
        action: "delete",
        resource: "customer record",
        dataSensitivity: "customer",
        decision: "denied",
      },
      timestamp,
    );
    expect(simulation.events.map((event) => event.eventType)).not.toContain(
      "agent.action.executed",
    );
    expect(simulation.events.at(-1)?.status).toBe("not_executed");
  });

  it("logs low-impact read actions without manufacturing an approval step", () => {
    const simulation = simulateAuditTrail(
      {
        actor: "Read-only agent",
        action: "read",
        resource: "public page",
        dataSensitivity: "public",
        decision: "approved",
      },
      timestamp,
    );
    expect(simulation.approvalRequired).toBe(false);
    expect(simulation.events.map((event) => event.eventType)).toEqual([
      "agent.action.requested",
      "agent.action.completed",
    ]);
  });
});
