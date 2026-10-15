import { describe, expect, it } from "vitest";
import { buildGovernanceSnapshotRequest } from "./snapshot-request";

describe("buildGovernanceSnapshotRequest", () => {
  it("refuses to create a snapshot while any policy value is unknown", () => {
    expect(
      buildGovernanceSnapshotRequest({
        autonomy_enabled: true,
        allow_high_impact_actions: false,
        strict_policy_lock: null,
        policy_change_human_validation: true,
      }),
    ).toBeNull();
  });

  it("returns only the explicitly selected policy values and a trimmed note", () => {
    expect(
      buildGovernanceSnapshotRequest(
        {
          autonomy_enabled: true,
          allow_high_impact_actions: false,
          strict_policy_lock: true,
          policy_change_human_validation: false,
        },
        "  Reviewed with security  ",
      ),
    ).toEqual({
      autonomy_enabled: true,
      allow_high_impact_actions: false,
      strict_policy_lock: true,
      policy_change_human_validation: false,
      notes: "Reviewed with security",
    });
  });
});
