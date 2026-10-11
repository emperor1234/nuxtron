"use client";

import { useState, type FormEvent } from "react";
import { scanMcpConfig, type McpScanResult } from "../_lib/mcp-scan";
import styles from "../tools.module.css";

const SAMPLE_CONFIG = JSON.stringify(
  {
    mcpServers: {
      example: {
        command: "node",
        args: ["./server.js"],
        env: { LOG_LEVEL: "info" },
      },
    },
  },
  null,
  2,
);

export function McpSecurityScanner() {
  const [configText, setConfigText] = useState("");
  const [result, setResult] = useState<McpScanResult | null>(null);

  function analyze(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setResult(scanMcpConfig(configText));
  }

  return (
    <>
      <form className={styles.toolForm} onSubmit={analyze}>
        <div className={styles.field}>
          <label className={styles.label} htmlFor="mcp-config">
            MCP client configuration (JSON)
          </label>
          <textarea
            id="mcp-config"
            className={styles.textarea}
            spellCheck={false}
            maxLength={150_000}
            placeholder={
              '{\n  "mcpServers": {\n    "example": { "command": "node", "args": ["server.js"] }\n  }\n}'
            }
            value={configText}
            onChange={(event) => {
              setConfigText(event.target.value);
              setResult(null);
            }}
          />
          <p className={styles.helpText}>
            The scanner parses the pasted JSON in this browser; it does not
            submit or persist the configuration. Do not paste production
            secrets. Detected credential values are never shown in results.
          </p>
        </div>
        <div className={styles.actionRow}>
          <button
            className={styles.secondaryButton}
            type="button"
            onClick={() => {
              setConfigText(SAMPLE_CONFIG);
              setResult(null);
            }}
          >
            Load example
          </button>
          <button
            className={styles.actionButton}
            type="submit"
            disabled={!configText.trim()}
          >
            Scan configuration
          </button>
        </div>
      </form>

      {result?.error ? (
        <p className={styles.errorMessage} role="alert">
          {result.error}
        </p>
      ) : null}

      {result && !result.error ? (
        <section
          className={styles.resultPanel}
          aria-live="polite"
          aria-labelledby="mcp-results-heading"
        >
          <h2 className={styles.resultHeading} id="mcp-results-heading">
            Static scan results
          </h2>
          <p className={styles.resultIntro}>
            Reviewed {result.serversAnalyzed} server configuration
            {result.serversAnalyzed === 1 ? "" : "s"}; found{" "}
            {result.findings.length} heuristic item
            {result.findings.length === 1 ? "" : "s"}.
          </p>
          {result.findings.length > 0 ? (
            <ul className={styles.resultList}>
              {result.findings.map((finding) => (
                <li
                  className={styles.resultCard}
                  key={`${finding.server}:${finding.id}`}
                >
                  <div className={styles.resultTop}>
                    <span className={styles.resultLabel}>{finding.title}</span>
                    <span
                      className={styles.resultBadge}
                      data-severity={finding.severity}
                    >
                      {finding.severity} · {finding.server}
                    </span>
                  </div>
                  <p className={styles.resultDetail}>{finding.detail}</p>
                </li>
              ))}
            </ul>
          ) : (
            <div className={styles.resultCard}>
              <div className={styles.resultTop}>
                <span className={styles.resultLabel}>
                  No static findings detected
                </span>
                <span className={styles.resultBadge} data-state="allowed">
                  Review still required
                </span>
              </div>
              <p className={styles.resultDetail}>
                A clean heuristic scan does not establish that the server, its
                dependencies, or its behavior is safe.
              </p>
            </div>
          )}
        </section>
      ) : null}

      <p className={styles.disclaimer}>
        This is a static heuristic check, not a penetration test, runtime
        monitor, or certification. It cannot inspect server source code or prove
        behavior. Review the publisher and source, pin dependencies, use least
        privilege and sandboxing, require approval for sensitive actions, and
        keep credentials in a secure secret manager.
      </p>
    </>
  );
}
