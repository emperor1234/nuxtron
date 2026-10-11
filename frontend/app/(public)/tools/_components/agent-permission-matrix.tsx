"use client";

import { useState, type FormEvent } from "react";
import {
  buildPermissionMatrix,
  PERMISSION_ACTIONS,
  type DataSensitivity,
  type PermissionActionId,
  type PermissionMatrixRow,
} from "../_lib/permissions";
import styles from "../tools.module.css";

const SENSITIVITY_OPTIONS: readonly {
  value: DataSensitivity;
  label: string;
}[] = [
  { value: "public", label: "Public" },
  { value: "internal", label: "Internal" },
  { value: "customer", label: "Customer data" },
  { value: "restricted", label: "Restricted / security-sensitive" },
];

export function AgentPermissionMatrix() {
  const [agentName, setAgentName] = useState("Content research agent");
  const [dataSensitivity, setDataSensitivity] =
    useState<DataSensitivity>("internal");
  const [actions, setActions] = useState<PermissionActionId[]>([
    "read",
    "draft",
  ]);
  const [rows, setRows] = useState<PermissionMatrixRow[] | null>(null);
  const [error, setError] = useState("");

  function toggleAction(action: PermissionActionId, checked: boolean) {
    setActions((current) =>
      checked
        ? [...new Set([...current, action])]
        : current.filter((item) => item !== action),
    );
    setRows(null);
  }

  function generate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (actions.length === 0) {
      setError("Select at least one proposed capability to build a matrix.");
      setRows(null);
      return;
    }
    setError("");
    setRows(buildPermissionMatrix({ agentName, dataSensitivity, actions }));
  }

  return (
    <>
      <form className={styles.toolForm} onSubmit={generate}>
        <div className={styles.formGrid}>
          <div className={styles.field}>
            <label className={styles.label} htmlFor="permission-agent-name">
              Agent name
            </label>
            <input
              id="permission-agent-name"
              className={styles.input}
              maxLength={80}
              value={agentName}
              onChange={(event) => {
                setAgentName(event.target.value);
                setRows(null);
              }}
              placeholder="For example, Content research agent"
            />
          </div>
          <div className={styles.field}>
            <label
              className={styles.label}
              htmlFor="permission-data-sensitivity"
            >
              Highest data sensitivity
            </label>
            <select
              id="permission-data-sensitivity"
              className={styles.select}
              value={dataSensitivity}
              onChange={(event) => {
                setDataSensitivity(event.target.value as DataSensitivity);
                setRows(null);
              }}
            >
              {SENSITIVITY_OPTIONS.map((option) => (
                <option value={option.value} key={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
          <div className={`${styles.field} ${styles.fieldFull}`}>
            <span className={styles.label}>What may the agent do?</span>
            <div className={styles.optionGrid}>
              {PERMISSION_ACTIONS.map((action) => (
                <label className={styles.option} key={action.id}>
                  <input
                    type="checkbox"
                    checked={actions.includes(action.id)}
                    onChange={(event) =>
                      toggleAction(action.id, event.target.checked)
                    }
                  />
                  <span>{action.label}</span>
                </label>
              ))}
            </div>
          </div>
        </div>
        <div className={styles.actionRow}>
          <button className={styles.actionButton} type="submit">
            Generate permission matrix
          </button>
        </div>
      </form>

      {error ? (
        <p className={styles.errorMessage} role="alert">
          {error}
        </p>
      ) : null}

      {rows ? (
        <section
          className={styles.resultPanel}
          aria-live="polite"
          aria-labelledby="permission-results-heading"
        >
          <h2 className={styles.resultHeading} id="permission-results-heading">
            Recommended starting matrix
          </h2>
          <p className={styles.resultIntro}>
            Principal: <strong>{agentName.trim() || "Unnamed agent"}</strong>.
            Scope is limited to {dataSensitivity.toLowerCase()} data. Treat each
            row as a design prompt, not an automatically enforced permission.
          </p>
          <div className={styles.matrixScroller}>
            <table className={styles.matrixTable}>
              <thead>
                <tr>
                  <th scope="col">Capability</th>
                  <th scope="col">Least-privilege grant</th>
                  <th scope="col">Approval</th>
                  <th scope="col">Audit evidence</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.action}>
                    <th scope="row">{row.label}</th>
                    <td>
                      {row.access}
                      <br />
                      <span className={styles.resultDetail}>
                        {row.dataScope}
                      </span>
                    </td>
                    <td>{row.approval}</td>
                    <td>{row.audit}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}

      <p className={styles.disclaimer}>
        This matrix is a planning aid, not an authorization policy or compliance
        assessment. Implement permissions in the connected systems, validate
        them server-side for every action, and review restricted-data access
        with your policy owner.
      </p>
    </>
  );
}
