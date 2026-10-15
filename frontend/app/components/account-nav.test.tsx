import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const pathname = vi.hoisted(() => ({ current: "/account/orders" }));

vi.mock("next/navigation", () => ({
  usePathname: () => pathname.current,
}));

import AccountNav from "./account-nav";

describe("AccountNav", () => {
  afterEach(cleanup);

  beforeEach(() => {
    pathname.current = "/account/orders";
  });

  it("exposes a named navigation landmark and identifies the current route", () => {
    render(<AccountNav />);

    expect(screen.getByRole("navigation", { name: "Account sections" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Orders" }).getAttribute("aria-current")).toBe("page");
    expect(screen.getByRole("link", { name: "Billing & Credits" }).getAttribute("aria-current")).toBeNull();
  });

  it("keeps the billing section current on billing result routes", () => {
    pathname.current = "/billing/success";
    render(<AccountNav />);

    expect(screen.getByRole("link", { name: "Billing & Credits" }).getAttribute("aria-current")).toBe("page");
  });
});
