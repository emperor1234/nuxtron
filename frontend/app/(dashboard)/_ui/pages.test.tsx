import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const { apiGet, apiSend } = vi.hoisted(() => ({ apiGet: vi.fn(), apiSend: vi.fn() }));
vi.mock("@/app/lib/api-client", () => ({ resolveSessionTenant: () => "tenant-a" }));
vi.mock("@/app/lib/platform-api", () => ({ apiGet, apiSend }));

import AiVisibilityPage from "../ai-visibility-dashboard/page";
import BenchmarksPage from "../benchmarks/page";
import CrmPage from "../crm/page";
import PlaybooksPage from "../playbooks/page";
import BrandKitPage from "../studio/brand-kit/page";
import WorkflowsPage from "../workflows/page";

afterEach(() => cleanup());
beforeEach(() => {
  apiGet.mockReset();
  apiSend.mockReset();
});

describe("empty workspaces show honest empty states", () => {
  it("CRM lists no contacts and invents none", async () => {
    apiGet.mockResolvedValue({ contacts: [], total: 0 });
    render(<CrmPage />);
    expect(await screen.findByText("No contacts yet")).toBeTruthy();
    expect(apiGet).toHaveBeenCalledWith(expect.stringContaining("/crm/contacts"), "tenant-a");
  });

  it("Workflows, Benchmarks and Playbooks show empty states", async () => {
    apiGet.mockImplementation((path: string) => {
      if (path.startsWith("/workflows")) return Promise.resolve({ workflows: [] });
      if (path === "/benchmarks") return Promise.resolve({ benchmarks: [] });
      if (path === "/playbooks") return Promise.resolve({ playbooks: [] });
      return Promise.resolve({ runs: [] });
    });
    render(<WorkflowsPage />);
    expect(await screen.findByText("No workflows yet")).toBeTruthy();
    cleanup();
    render(<BenchmarksPage />);
    expect(await screen.findByText("Nothing recorded")).toBeTruthy();
    cleanup();
    render(<PlaybooksPage />);
    expect(await screen.findByText("No playbooks")).toBeTruthy();
  });

  it("AI Visibility shows zero sites without a fake score", async () => {
    apiGet.mockImplementation((path: string) =>
      path.startsWith("/ai-crawler/dashboard")
        ? Promise.resolve({ window_hours: 168, summary: { total_hits: 0, ai_crawler_hits: 0, blocked_hits: 0, sites_registered: 0, sites_with_snippet: 0 }, top_crawlers: [], top_pages: [] })
        : Promise.resolve({ sites: [] }),
    );
    render(<AiVisibilityPage />);
    expect(await screen.findByText("No sites yet")).toBeTruthy();
  });
});

describe("forms validate before they call the backend", () => {
  it("CRM refuses a contact with no first name", async () => {
    apiGet.mockResolvedValue({ contacts: [], total: 0 });
    render(<CrmPage />);
    fireEvent.click((await screen.findAllByText("Add contact"))[0]);
    fireEvent.click(screen.getAllByText("Add contact").at(-1)!);
    await waitFor(() => expect(screen.queryByText("Enter a first name.")).toBeTruthy());
    expect(apiSend).not.toHaveBeenCalled();
  });

  it("Benchmarks refuses an empty record", async () => {
    apiGet.mockResolvedValue({ benchmarks: [] });
    render(<BenchmarksPage />);
    fireEvent.click((await screen.findAllByText("Record a result"))[0]);
    fireEvent.click(await screen.findByText("Save"));
    await waitFor(() => expect(screen.queryByText("Name the metric.")).toBeTruthy());
    expect(apiSend).not.toHaveBeenCalled();
  });
});

describe("Brand Kit", () => {
  const kit = {
    colors: { primary: "#2563C9", secondary: "#22CDEA", accent: "#0B1330", background: "#FFFFFF", text: "#0B1330", muted: "#5B6480" },
    fonts: { heading: { family: "Inter", weight: "700", size_px: 32 }, body: { family: "Inter", weight: "400", size_px: 16 }, display: { family: "Inter", weight: "800", size_px: 48 } },
    logos: { main: "", icon: "", dark_variant: "", light_variant: "" },
    voice: { tone_preset: "professional" },
    messaging: {},
    writing_rules: {},
    knowledge_base_count: 0,
  };

  it("rejects a malformed colour and saves a valid one to the colours route", async () => {
    apiGet.mockResolvedValue({ brand_kit: kit });
    apiSend.mockResolvedValue({});
    render(<BrandKitPage />);
    const primary = (await screen.findAllByLabelText("Primary"))[0] as HTMLInputElement;
    fireEvent.change(primary, { target: { value: "blue" } });
    fireEvent.click(screen.getAllByText("Save")[0]);
    await waitFor(() => expect(screen.queryByText(/six-digit hex/)).toBeTruthy());
    expect(apiSend).not.toHaveBeenCalled();
    fireEvent.change(primary, { target: { value: "#112233" } });
    fireEvent.click(screen.getAllByText("Save")[0]);
    await waitFor(() => expect(apiSend).toHaveBeenCalled());
    expect(apiSend.mock.calls[0][0]).toBe("/brand-kit/colors");
    expect(apiSend.mock.calls[0][2]).toMatchObject({ primary: "#112233" });
  });
});
