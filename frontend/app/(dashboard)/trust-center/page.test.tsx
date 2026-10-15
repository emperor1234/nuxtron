import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import TrustCenterPage from "./page";

const { apiGet, apiPost } = vi.hoisted(() => ({ apiGet: vi.fn(), apiPost: vi.fn() }));
vi.mock("@/app/lib/api-client", () => ({ apiGet, apiPost }));
vi.mock("@/app/components/institutional-ai-widgets", () => ({ default: () => null }));

afterEach(cleanup);
beforeEach(() => {
  vi.clearAllMocks();
  apiGet.mockImplementation((path: string) =>
    Promise.resolve(
      path.endsWith("/posture")
        ? { posture_score: 90, open_incidents: 2, critical_open_incidents: 0, active_approval_chains: 1, policy_changes_recorded: 3 }
        : path.endsWith("/incidents")
          ? { incidents: [] }
          : path.endsWith("/approval-chains")
            ? { chains: [] }
            : { history: [] },
    ),
  );
  apiPost.mockResolvedValue({ snapshot_id: "snapshot-123", status: "captured" });
});

describe("Trust Center governance snapshot", () => {
  it("requires explicit self-attested policy values and confirmation before writing", async () => {
    render(<TrustCenterPage />);
    await screen.findByText("Posture Score");
    fireEvent.click(screen.getByRole("button", { name: "Capture Snapshot" }));

    const capture = screen.getByRole("button", { name: "Capture this snapshot" });
    expect((capture as HTMLButtonElement).disabled).toBe(true);
    fireEvent.change(screen.getByLabelText("Autonomy enabled"), { target: { value: "true" } });
    fireEvent.change(screen.getByLabelText("High-impact actions allowed"), { target: { value: "false" } });
    fireEvent.change(screen.getByLabelText("Strict policy lock"), { target: { value: "true" } });
    fireEvent.change(screen.getByLabelText("Human validation for policy changes"), { target: { value: "false" } });
    expect((capture as HTMLButtonElement).disabled).toBe(true);

    fireEvent.click(screen.getByLabelText("I confirm these values reflect the currently configured policies."));
    expect((capture as HTMLButtonElement).disabled).toBe(false);
    fireEvent.click(capture);

    await waitFor(() => expect(apiPost).toHaveBeenCalledTimes(1));
    expect(apiPost).toHaveBeenCalledWith(
      "/trust-center/snapshots",
      expect.objectContaining({
        autonomy_enabled: true,
        allow_high_impact_actions: false,
        strict_policy_lock: true,
        policy_change_human_validation: false,
        notes: expect.stringContaining("not independently verified"),
      }),
      "",
    );
    const posted = apiPost.mock.calls[0]?.[1] as Record<string, unknown>;
    expect(posted).not.toHaveProperty("active_approval_chains");
    expect(posted).not.toHaveProperty("open_incidents");
    expect((await screen.findByRole("status")).textContent).toContain("snapshot-123 captured");
  });
});
