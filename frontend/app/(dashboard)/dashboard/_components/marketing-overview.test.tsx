import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import MarketingOverview from "./marketing-overview";

vi.mock("./number-ticker", () => ({
  default: ({ value }: { value: number }) => (
    <span>{new Intl.NumberFormat("en-US").format(value)}</span>
  ),
}));

const { apiGet, push } = vi.hoisted(() => ({ apiGet: vi.fn(), push: vi.fn() }));
vi.mock("@/app/lib/api-client", () => ({
  apiGet,
  resolveSessionTenant: () => "test-workspace",
}));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));
afterEach(cleanup);
beforeEach(() => {
  vi.clearAllMocks();
});

describe("workspace overview", () => {
  it("preserves zero values and clearly labels sample responses", async () => {
    apiGet.mockImplementation((path: string) =>
      Promise.resolve(
        path.includes("usage")
          ? { current_plan: "Starter", credit_balance: 0, source: "sample" }
          : path.includes("analyses")
            ? { total: 0, analyses: [] }
            : { modules: [] },
      ),
    );
    render(<MarketingOverview />);
    await screen.findByText("Preview data");
    expect(screen.getAllByText("0")).toHaveLength(3);
    expect(screen.getByText("Your research starts here")).toBeTruthy();
    expect(screen.queryByText("Live data")).toBeNull();
  });

  it("keeps a successful balance when other services fail, and retries", async () => {
    apiGet.mockImplementation((path: string) =>
      path.includes("usage")
        ? Promise.resolve({ current_plan: "Starter", credit_balance: 25 })
        : Promise.reject(new Error("Unavailable")),
    );
    render(<MarketingOverview />);
    await screen.findByText("Some workspace data couldn’t load");
    expect(screen.getByText("25")).toBeTruthy();
    expect(screen.getByText("History is unavailable")).toBeTruthy();
    apiGet.mockResolvedValue({
      current_plan: "Starter",
      credit_balance: 25,
      analyses: [],
      modules: [],
    });
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    await screen.findByText("Your research starts here");
    expect(screen.queryByText("Some workspace data couldn’t load")).toBeNull();
  });

  it("treats malformed successful responses as unavailable", async () => {
    apiGet.mockResolvedValue({});
    render(<MarketingOverview />);
    await screen.findByText("Data unavailable");
    expect(screen.getAllByText("—")).toHaveLength(4);
    expect(screen.queryByText("Your research starts here")).toBeNull();
  });

  it("rejects credentials in domains and navigates using a normalized hostname", async () => {
    apiGet.mockResolvedValue({});
    render(<MarketingOverview />);
    await waitFor(() => expect(apiGet).toHaveBeenCalledTimes(3));
    const input = screen.getByLabelText("Website or domain");
    fireEvent.change(input, {
      target: { value: "https://user:pass@example.com" },
    });
    fireEvent.click(
      screen.getByRole("button", { name: "Analyze" }),
    );
    expect(screen.getByRole("alert").textContent).toContain("valid domain");
    expect(push).not.toHaveBeenCalled();
    fireEvent.change(input, { target: { value: "https://Example.com/path" } });
    fireEvent.click(
      screen.getByRole("button", { name: "Analyze" }),
    );
    expect(push).toHaveBeenCalledWith(
      "/seo/domain-overview?domain=example.com",
    );
  });
});
