"use client";

import { useEffect, useState, type FormEvent } from "react";
import {
  simulateAuditTrail,
  requiresApproval,
  type AuditSensitivity,
  type SimulatedAction,
  type SimulatedDecision,
  type AuditSimulation,
} from "../_lib/audit-simulator";
import styles from "../tools.module.css";

const ACTION_OPTIONS: readonly { value: SimulatedAction; label: string }[] = [
  { value: "read", label: "Read approved data" },
  { value: "draft", label: "Create a draft" },
  { value: "update", label: "Update a record" },
  { value: "publish", label: "Publish or send externally" },
  { value: "delete", label: "Delete a record" },
  { value: "change-access", label: "Change access or permissions" },
];

const SENSITIVITY_OPTIONS: readonly {
  value: AuditSensitivity;
  label: string;
}[] = [
  { value: "public", label: "Public" },
  { value: "internal", label: "Internal" },
  { value: "customer", label: "Customer data" },
  { value: "restricted", label: "Restricted / security-sensitive" },
];

export function AgentAuditLogSimulator() {
  const [actor, setActor] = useState("Growth agent");
  const [resource, setResource] = useState("Campaign draft");
  const [action, setAction] = useState<SimulatedAction>("publish");
  const [dataSensitivity, setDataSensitivity] =
    useState<AuditSensitivity>("internal");
  const [decision, setDecision] = useState<SimulatedDecision>("approved");
  const [simulation, setSimulation] = useState<AuditSimulation | null>(null);
  const [isHydrated, setIsHydrated] = useState(false);
  const needsApproval = requiresApproval(action, dataSensitivity);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setIsHydrated(true);
  }, []);

  function simulate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSimulation(
      simulateAuditTrail({
        actor,
        resource,
        action,
        dataSensitivity,
        decision,
      }),
    );
  }

  return (
    <>
      <form className={styles.toolForm} onSubmit={simulate}>
        <div className={styles.formGrid}>
          <div className={styles.field}>
            <label className={styles.label} htmlFor="audit-actor">
              Agent / principal
            </label>
            <input
              id="audit-actor"
              className={styles.input}
              maxLength={80}
              value={actor}
              onChange={(event) => {
                setActor(event.target.value);
                setSimulation(null);
              }}
            />
          </div>
          <div className={styles.field}>
            <label className={styles.label} htmlFor="audit-resource">
              Resource or target
            </label>
            <input
              id="audit-resource"
              className={styles.input}
              maxLength={100}
              value={resource}
              onChange={(event) => {
                setResource(event.target.value);
                setSimulation(null);
              }}
            />
          </div>
          <div className={styles.field}>
            <label className={styles.label} htmlFor="audit-action">
              Proposed action
            </label>
            <select
              id="audit-action"
              className={styles.select}
              value={action}
              onChange={(event) => {
                setAction(event.target.value as SimulatedAction);
                setSimulation(null);
              }}
            >
              {ACTION_OPTIONS.map((option) => (
                <option value={option.value} key={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
          <div className={styles.field}>
            <label className={styles.label} htmlFor="audit-sensitivity">
              Data sensitivity
            </label>
            <select
              id="audit-sensitivity"
              className={styles.select}
              value={dataSensitivity}
              onChange={(event) => {
                setDataSensitivity(event.target.value as AuditSensitivity);
                setSimulation(null);
              }}
            >
              {SENSITIVITY_OPTIONS.map((option) => (
                <option value={option.value} key={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
          {needsApproval ? (
            <div className={styles.field}>
              <label className={styles.label} htmlFor="audit-decision">
                Simulated reviewer decision
              </label>
              <select
                id="audit-decision"
                className={styles.select}
                value={decision}
                onChange={(event) => {
                  setDecision(event.target.value as SimulatedDecision);
                  setSimulation(null);
                }}
              >
                <option value="approved">Approved</option>
                <option value="denied">Denied</option>
              </select>
            </div>
          ) : (
            <p className={styles.helpText}>
              This low-impact scenario is logged without a per-action approval
              step in the sample policy.
            </p>
          )}
        </div>
        <div className={styles.actionRow}>
          <button
            className={styles.actionButton}
            type="submit"
            disabled={!isHydrated}
          >
            Simulate audit trail
          </button>
        </div>
      </form>

      {simulation ? (
        <section
          className={styles.resultPanel}
          aria-live="polite"
          aria-labelledby="audit-results-heading"
        >
          <div className={styles.resultTop}>
            <h2 className={styles.resultHeading} id="audit-results-heading">
              Illustrative event trail
            </h2>
            <span
              className={styles.resultBadge}
              data-state={
                simulation.events.at(-1)?.status === "not_executed"
                  ? "blocked"
                  : "allowed"
              }
            >
              Simulation only
            </span>
          </div>
          <p className={styles.resultIntro}>
            {simulation.approvalRequired
              ? "Approval is required for this action under the sample policy."
              : "This low-impact action is recorded without an approval step under the sample policy."}{" "}
            No connected system was called.
          </p>
          <ol className={styles.timeline}>
            {simulation.events.map((event, index) => (
              <li className={styles.timelineItem} key={event.id}>
                <span className={styles.timelineMarker} aria-hidden="true">
                  {index + 1}
                </span>
                <div className={styles.timelineContent}>
                  <div className={styles.resultTop}>
                    <span className={styles.resultLabel}>
                      {event.eventType}
                    </span>
                    <span
                      className={styles.resultBadge}
                      data-state={
                        event.status === "denied" ||
                        event.status === "not_executed"
                          ? "blocked"
                          : event.status === "pending_approval"
                            ? "partial"
                            : "allowed"
                      }
                    >
                      {event.status.replaceAll("_", " ")}
                    </span>
                  </div>
                  <p className={styles.resultDetail}>{event.note}</p>
                  <p className={styles.resultDetail}>
                    <time dateTime={event.timestamp}>
                      {new Date(event.timestamp).toLocaleString()}
                    </time>{" "}
                    · {event.actor} · {event.resource}
                  </p>
                </div>
              </li>
            ))}
          </ol>
          <pre className={styles.codeBlock}>
            {JSON.stringify(simulation, null, 2)}
          </pre>
        </section>
      ) : null}

      <p className={styles.disclaimer}>
        This page only simulates events in your browser. It creates no real
        approval, audit record, or external action. Production audit evidence
        must be generated by the system that authorizes and executes the
        operation, with secrets and personal data redacted as appropriate.
      </p>
    </>
  );
}
