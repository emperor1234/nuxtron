import { describe, expect, it } from "vitest";
import { buildPermissionMatrix } from "./permissions";

describe("permission matrix generator", () => {
  it("creates rows only for selected actions and identifies the agent principal", () => {
    const rows = buildPermissionMatrix({
      agentName: "  Content assistant  ",
      dataSensitivity: "internal",
      actions: ["read", "publish"],
    });
    expect(rows).toHaveLength(2);
    expect(rows[0].principal).toBe("Content assistant");
    expect(rows[0].dataScope).toContain("internal data");
    expect(rows[1].approval).toContain("explicit approval");
    expect(rows[0].access).toContain("Read only");
  });

  it("requires policy-owner review before restricted read access", () => {
    const rows = buildPermissionMatrix({
      agentName: "Security agent",
      dataSensitivity: "restricted",
      actions: ["read"],
    });
    expect(rows[0].approval).toContain("policy-owner review");
  });

  it("recommends keeping destructive and access-changing rights separate", () => {
    const rows = buildPermissionMatrix({
      agentName: "Agent",
      dataSensitivity: "customer",
      actions: ["destructive"],
    });
    expect(rows[0].access).toContain("Not granted by default");
    expect(rows[0].approval).toContain("dual approval");
  });
});
