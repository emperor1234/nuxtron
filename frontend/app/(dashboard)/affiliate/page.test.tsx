import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import AffiliatePage from "./page";

const { apiPost } = vi.hoisted(() => ({ apiPost: vi.fn() }));
vi.mock("@/app/lib/api-client", () => ({
  apiPost,
  resolveSessionTenant: () => "workspace-test",
}));

afterEach(cleanup);
beforeEach(() => {
  vi.clearAllMocks();
  Object.defineProperty(navigator, "clipboard", {
    configurable: true,
    value: { writeText: vi.fn().mockResolvedValue(undefined) },
  });
});

describe("Affiliate referrals", () => {
  it("requires an explicit valid email and referral code, then submits those values once", async () => {
    let resolveClaim: ((value: unknown) => void) | undefined;
    apiPost.mockImplementation(
      () => new Promise((resolve) => { resolveClaim = resolve; }),
    );

    render(<AffiliatePage />);

    expect(screen.queryByText("workspace-test")).toBeNull();
    const email = screen.getByLabelText("Email for this referral claim");
    const code = screen.getByLabelText("Existing referral code");
    const claim = screen.getByRole("button", { name: "Claim referral" });

    expect((claim as HTMLButtonElement).disabled).toBe(true);
    fireEvent.change(code, { target: { value: "SAVE-7" } });
    fireEvent.change(email, { target: { value: "not-an-email" } });
    expect((claim as HTMLButtonElement).disabled).toBe(true);

    fireEvent.change(email, { target: { value: "member@example.com" } });
    expect((claim as HTMLButtonElement).disabled).toBe(false);
    fireEvent.click(claim);

    await waitFor(() => expect(apiPost).toHaveBeenCalledTimes(1));
    expect(apiPost).toHaveBeenCalledWith(
      "/engagement/referrals/claim",
      { referral_code: "SAVE-7", referred_email: "member@example.com" },
      "workspace-test",
    );
    expect((claim as HTMLButtonElement).disabled).toBe(true);

    resolveClaim?.({ status: "ok" });
    expect((await screen.findByRole("status")).textContent).toContain("Referral claimed");
  });

  it("provides a copy action only after the server returns a real referral code", async () => {
    apiPost.mockResolvedValue({ profile: { referral_code: "NX-REAL-42" } });
    render(<AffiliatePage />);

    fireEvent.click(screen.getByRole("button", { name: "Generate referral code" }));
    const generatedCode = await screen.findByLabelText("Your referral code");
    expect((generatedCode as HTMLInputElement).value).toBe("NX-REAL-42");
    const copy = screen.getByRole("button", { name: "Copy referral code" });
    fireEvent.click(copy);

    await waitFor(() => {
      expect(navigator.clipboard.writeText).toHaveBeenCalledWith("NX-REAL-42");
    });
    expect((await screen.findByRole("status")).textContent).toContain("copied");
  });
});
