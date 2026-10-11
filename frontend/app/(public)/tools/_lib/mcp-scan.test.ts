import { describe, expect, it } from "vitest";
import { scanMcpConfig } from "./mcp-scan";

describe("MCP configuration scanner", () => {
  it("returns a useful parse error for malformed JSON", () => {
    const result = scanMcpConfig("{ broken");
    expect(result.error).toContain("not valid JSON");
    expect(result.serversAnalyzed).toBe(0);
  });

  it("accepts a minimal reviewed stdio config without findings", () => {
    const result = scanMcpConfig(
      JSON.stringify({
        mcpServers: { notes: { command: "node", args: ["server.js"] } },
      }),
    );
    expect(result.serversAnalyzed).toBe(1);
    expect(result.findings).toEqual([]);
  });

  it("flags shell execution and embedded credentials without exposing the value", () => {
    const secret = "test_secret_value_123456789";
    const result = scanMcpConfig(
      JSON.stringify({
        mcpServers: {
          risky: {
            command: "bash",
            args: ["-c", "run-server"],
            env: { SERVICE_API_KEY: secret },
          },
        },
      }),
    );
    const serialized = JSON.stringify(result);
    expect(result.findings.map((finding) => finding.id)).toContain(
      "shell-execution",
    );
    expect(result.findings.map((finding) => finding.id)).toContain(
      "inline-shell-command",
    );
    expect(result.findings.map((finding) => finding.id)).toContain(
      "embedded-secret",
    );
    expect(serialized).not.toContain(secret);
  });

  it("flags remote HTTP and wildcard grants while accepting HTTPS endpoints", () => {
    const result = scanMcpConfig(
      JSON.stringify({
        servers: {
          insecure: { url: "http://remote.example/mcp", allowedTools: ["*"] },
          secure: { url: "https://remote.example/mcp" },
        },
      }),
    );
    expect(
      result.findings.some(
        (finding) =>
          finding.server === "insecure" && finding.id === "remote-http",
      ),
    ).toBe(true);
    expect(
      result.findings.some(
        (finding) =>
          finding.server === "insecure" && finding.id === "wildcard-permission",
      ),
    ).toBe(true);
    expect(
      result.findings.some(
        (finding) =>
          finding.server === "secure" && finding.id === "remote-http",
      ),
    ).toBe(false);
  });

  it("redacts credentials in command arguments and endpoint URL userinfo", () => {
    const secret = "secret-value-that-must-not-appear";
    const result = scanMcpConfig(
      JSON.stringify({
        mcpServers: {
          args: { command: "node", args: ["server.js", "--api-key", secret] },
          url: { url: `https://user:${secret}@remote.example/mcp` },
        },
      }),
    );
    const serialized = JSON.stringify(result);
    expect(result.findings.map((finding) => finding.id)).toContain(
      "inline-argument-secret",
    );
    expect(result.findings.map((finding) => finding.id)).toContain(
      "embedded-url-credential",
    );
    expect(serialized).not.toContain(secret);
  });

  it("warns when a server entry has no launch command or URL", () => {
    const result = scanMcpConfig(JSON.stringify({ mcpServers: { empty: {} } }));
    expect(result.findings.map((finding) => finding.id)).toContain(
      "missing-transport",
    );
  });

  it("reports permissive tool schemas as a heuristic", () => {
    const result = scanMcpConfig(
      JSON.stringify({
        mcpServers: {
          tools: {
            tools: [
              {
                name: "search",
                inputSchema: { type: "object" },
              },
            ],
          },
        },
      }),
    );
    expect(result.findings.map((finding) => finding.id)).toContain(
      "open-schema-0",
    );
  });
});
