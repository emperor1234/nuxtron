export type McpFinding = {
  id: string;
  severity: "high" | "medium" | "low";
  server: string;
  title: string;
  detail: string;
};

export type McpScanResult = {
  serversAnalyzed: number;
  findings: McpFinding[];
  error?: string;
};

type JsonRecord = Record<string, unknown>;

function isRecord(value: unknown): value is JsonRecord {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isPlaceholder(value: string): boolean {
  const normalized = value.trim().toLowerCase();
  return (
    !normalized ||
    /^(?:<[^>]+>|\$\{[^}]+\}|\$\([^)]+\)|your[-_ ].*|replace[-_ ].*|changeme|change-me|redacted|example|placeholder|xxxxx+)$/i.test(
      normalized,
    ) ||
    /^(?:bearer|basic)\s+\$\{[^}]+\}$/i.test(value.trim())
  );
}

function looksLikeSecret(value: unknown): boolean {
  if (typeof value !== "string") {
    return (
      value !== undefined && value !== null && value !== false && value !== 0
    );
  }
  return !isPlaceholder(value);
}

const SECRET_NAME =
  /(?:api[_-]?key|access[_-]?token|refresh[_-]?token|secret|password|credential|private[_-]?key|authorization)/i;
const SECRET_ARGUMENT_NAME =
  /^--?(?:api[-_]?key|access[-_]?token|refresh[-_]?token|client[-_]?secret|token|secret|password|authorization)(?:=|$)/i;
const SHELLS = new Set([
  "sh",
  "bash",
  "zsh",
  "fish",
  "dash",
  "cmd",
  "cmd.exe",
  "powershell",
  "pwsh",
]);
const RUNTIME_FETCHERS = new Set([
  "npx",
  "bunx",
  "uvx",
  "pipx",
  "deno",
  "curl",
  "wget",
]);
const HIGH_IMPACT_TOOL =
  /\b(?:exec(?:ute)?|shell|delete|destroy|publish|send|transfer|payment|admin|permission|credential|secret|write[_ -]?file)\b/i;

function commandName(command: string): string {
  return (
    command.split(/[\\/]/).filter(Boolean).at(-1)?.toLowerCase() ??
    command.toLowerCase()
  );
}

function hasInlineSecretArgument(args: readonly string[]): boolean {
  for (let index = 0; index < args.length; index += 1) {
    const argument = args[index].trim();
    const separator = argument.indexOf("=");
    const name = separator >= 0 ? argument.slice(0, separator) : argument;
    if (!SECRET_ARGUMENT_NAME.test(name)) continue;
    const value =
      separator >= 0 ? argument.slice(separator + 1) : (args[index + 1] ?? "");
    if (looksLikeSecret(value)) return true;
  }
  return false;
}

function addFinding(
  findings: McpFinding[],
  server: string,
  id: string,
  severity: McpFinding["severity"],
  title: string,
  detail: string,
) {
  if (
    !findings.some((finding) => finding.id === id && finding.server === server)
  ) {
    findings.push({ id, severity, server, title, detail });
  }
}

function scanToolDefinitions(
  value: unknown,
  serverName: string,
  findings: McpFinding[],
) {
  if (!Array.isArray(value)) return;
  for (const [index, item] of value.entries()) {
    if (!isRecord(item)) continue;
    const name =
      typeof item.name === "string" ? item.name : `Tool ${index + 1}`;
    const description =
      typeof item.description === "string" ? item.description : "";
    const combined = `${name} ${description}`;
    if (HIGH_IMPACT_TOOL.test(combined)) {
      addFinding(
        findings,
        serverName,
        `high-impact-tool-${index}`,
        "medium",
        `Review high-impact tool: ${name}`,
        "This tool name or description suggests a write, execution, publishing, deletion, permission, or financial capability. Confirm its scope and require approval where appropriate.",
      );
    }
    const inputSchema = item.inputSchema;
    if (isRecord(inputSchema) && inputSchema.additionalProperties !== false) {
      addFinding(
        findings,
        serverName,
        `open-schema-${index}`,
        "medium",
        `Tool schema is not closed: ${name}`,
        "The input schema does not explicitly reject undeclared properties. Prefer additionalProperties: false and validate authorization separately.",
      );
    }
  }
}

export function scanMcpConfig(source: string): McpScanResult {
  if (source.length > 150_000) {
    return {
      serversAnalyzed: 0,
      findings: [],
      error: "Configuration is too large. Keep the pasted JSON under 150 KB.",
    };
  }

  let parsed: unknown;
  try {
    parsed = JSON.parse(source);
  } catch {
    return {
      serversAnalyzed: 0,
      findings: [],
      error:
        "This is not valid JSON. Check commas, quotes, and braces, then try again.",
    };
  }

  if (!isRecord(parsed)) {
    return {
      serversAnalyzed: 0,
      findings: [],
      error:
        "Expected a JSON object containing an mcpServers or servers object.",
    };
  }

  const servers = isRecord(parsed.mcpServers)
    ? parsed.mcpServers
    : isRecord(parsed.servers)
      ? parsed.servers
      : null;
  if (!servers) {
    return {
      serversAnalyzed: 0,
      findings: [],
      error: "Expected an mcpServers or servers object at the top level.",
    };
  }

  const findings: McpFinding[] = [];
  const entries = Object.entries(servers);

  for (const [serverName, rawConfig] of entries) {
    if (!isRecord(rawConfig)) {
      addFinding(
        findings,
        serverName,
        "invalid-server",
        "high",
        "Server entry is not an object",
        "Review the server configuration shape before using it.",
      );
      continue;
    }

    const command =
      typeof rawConfig.command === "string" ? rawConfig.command : "";
    const args = Array.isArray(rawConfig.args)
      ? rawConfig.args.filter(
          (item): item is string => typeof item === "string",
        )
      : [];
    const executable = commandName(command);
    const hasRemoteUrl =
      typeof rawConfig.url === "string" && rawConfig.url.trim().length > 0;

    if (!command && !hasRemoteUrl) {
      addFinding(
        findings,
        serverName,
        "missing-transport",
        "medium",
        "No server launch command or endpoint found",
        "The entry does not declare a stdio command or remote URL. Confirm that the selected MCP client supports this configuration shape.",
      );
    }

    if (SHELLS.has(executable)) {
      addFinding(
        findings,
        serverName,
        "shell-execution",
        "high",
        "Shell process configured",
        "A shell-launched server can execute commands with the host process's permissions. Review the exact command, sandbox it, and restrict filesystem and network access.",
      );
    }

    if (
      SHELLS.has(executable) &&
      args.some((argument) =>
        ["-c", "/c", "-command", "-encodedcommand"].includes(
          argument.toLowerCase(),
        ),
      )
    ) {
      addFinding(
        findings,
        serverName,
        "inline-shell-command",
        "high",
        "Inline shell command configured",
        "Inline commands are difficult to review and can hide behavior. Prefer a pinned, reviewed executable and explicit arguments.",
      );
    }

    if (
      RUNTIME_FETCHERS.has(executable) ||
      args.some((argument) =>
        /(?:^|\s)(?:curl|wget)\s+.*\|\s*(?:sh|bash)/i.test(argument),
      )
    ) {
      addFinding(
        findings,
        serverName,
        "runtime-package-fetch",
        "medium",
        "Runtime package or script fetcher detected",
        "Runtime downloads can change between launches. Pin versions and integrity, verify the publisher, and avoid piping remote content into a shell.",
      );
    }

    if (
      args.some(
        (argument) =>
          /^(?:\/|~(?:\/|$)|[A-Z]:\\)$/i.test(argument) ||
          /^(?:\/Users|\/home|C:\\Users)(?:\/|\\|$)/i.test(argument),
      )
    ) {
      addFinding(
        findings,
        serverName,
        "broad-filesystem-path",
        "high",
        "Broad filesystem path in arguments",
        "A root or home-directory path may grant wider file access than the server needs. Scope access to a dedicated, minimal directory.",
      );
    }

    if (hasInlineSecretArgument(args)) {
      addFinding(
        findings,
        serverName,
        "inline-argument-secret",
        "high",
        "Possible credential passed in command arguments",
        "A secret-like command-line flag appears to have a value. The value is never shown; pass credentials through a protected secret store or environment injection instead.",
      );
    }

    const env = isRecord(rawConfig.env) ? rawConfig.env : {};
    for (const [key, value] of Object.entries(env)) {
      if (SECRET_NAME.test(key) && looksLikeSecret(value)) {
        addFinding(
          findings,
          serverName,
          "embedded-secret",
          "high",
          "Possible inline credential in environment config",
          "A credential-like environment value appears to be populated. This scanner never displays the value. Use an OS or enterprise secret manager and rotate it if it has been exposed outside a trusted local session.",
        );
        break;
      }
    }

    const url = typeof rawConfig.url === "string" ? rawConfig.url : "";
    if (url) {
      try {
        const parsedUrl = new URL(url);
        const isLoopback = ["localhost", "127.0.0.1", "::1"].includes(
          parsedUrl.hostname.toLowerCase(),
        );
        if (parsedUrl.username || parsedUrl.password) {
          addFinding(
            findings,
            serverName,
            "embedded-url-credential",
            "high",
            "Credential embedded in endpoint URL",
            "The endpoint URL contains user-info credentials. The value is intentionally omitted; remove it from the URL and use a secure credential mechanism.",
          );
        }
        if (parsedUrl.protocol !== "https:" && !isLoopback) {
          addFinding(
            findings,
            serverName,
            "remote-http",
            "high",
            "Remote MCP endpoint does not use HTTPS",
            "A non-loopback HTTP endpoint can expose traffic in transit. Use HTTPS and verify the server identity.",
          );
        }
        if (isLoopback) {
          addFinding(
            findings,
            serverName,
            "loopback-endpoint",
            "low",
            "Loopback endpoint configured",
            "Confirm this endpoint is intentionally local and that it is not exposed through a proxy or port forward.",
          );
        }
      } catch {
        addFinding(
          findings,
          serverName,
          "invalid-url",
          "high",
          "Endpoint URL is invalid",
          "Use a well-formed HTTPS URL for a remote MCP server.",
        );
      }
    }

    const headers = isRecord(rawConfig.headers) ? rawConfig.headers : {};
    if (
      Object.entries(headers).some(
        ([key, value]) => SECRET_NAME.test(key) && looksLikeSecret(value),
      )
    ) {
      addFinding(
        findings,
        serverName,
        "embedded-header-secret",
        "high",
        "Possible inline credential in headers",
        "A populated authorization-like header was found. The value is intentionally omitted; move it to a secure credential store.",
      );
    }

    for (const key of ["tools", "toolDefinitions"]) {
      scanToolDefinitions(rawConfig[key], serverName, findings);
    }

    const permissions = [
      rawConfig.permissions,
      rawConfig.allowedTools,
      rawConfig.scopes,
    ];
    if (
      permissions.some(
        (value) => Array.isArray(value) && value.some((item) => item === "*"),
      )
    ) {
      addFinding(
        findings,
        serverName,
        "wildcard-permission",
        "high",
        "Wildcard permission detected",
        "A wildcard grant can expose more capabilities than intended. Replace it with a per-tool allowlist and verify authorization at execution time.",
      );
    }
  }

  return { serversAnalyzed: entries.length, findings };
}
