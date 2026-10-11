import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { seoHomepage } from "../../_content/seo";
import { DemoSection } from "./demo-section";

const originalVisibilityDescriptor = Object.getOwnPropertyDescriptor(
  document,
  "visibilityState",
);
const originalMatchMediaDescriptor = Object.getOwnPropertyDescriptor(
  window,
  "matchMedia",
);

afterEach(() => {
  cleanup();
  if (originalVisibilityDescriptor) {
    Object.defineProperty(document, "visibilityState", originalVisibilityDescriptor);
  } else {
    Reflect.deleteProperty(document, "visibilityState");
  }
  if (originalMatchMediaDescriptor) {
    Object.defineProperty(window, "matchMedia", originalMatchMediaDescriptor);
  } else {
    Reflect.deleteProperty(window, "matchMedia");
  }
});

describe("DemoSection playback", () => {
  it(
    "starts manual playback from current visibility before the visibility event state catches up",
    async () => {
      Object.defineProperty(window, "matchMedia", {
        configurable: true,
        value: (media: string) =>
          ({
            matches: media === "(prefers-reduced-motion: reduce)",
            media,
            onchange: null,
            addListener: () => undefined,
            removeListener: () => undefined,
            addEventListener: () => undefined,
            removeEventListener: () => undefined,
            dispatchEvent: () => true,
          }) as ReturnType<typeof window.matchMedia>,
      });
      Object.defineProperty(document, "visibilityState", {
        configurable: true,
        value: "hidden",
      });

      render(<DemoSection content={seoHomepage.demo} />);

      const tablist = screen.getByRole("tablist", {
        name: `${seoHomepage.demo.title}: demo views`,
      });
      const secondView = within(tablist).getByRole("tab", {
        name: "AI visibility",
      });
      fireEvent.click(secondView);
      await waitFor(() =>
        expect(secondView.getAttribute("aria-selected")).toBe("true"),
      );

      // Model the browser becoming visible before React has handled visibilitychange.
      Object.defineProperty(document, "visibilityState", {
        configurable: true,
        value: "visible",
      });
      fireEvent.click(screen.getByRole("button", { name: "Play product tour" }));

      await waitFor(() => {
        const pauseButton = screen.getByRole("button", {
          name: "Pause product tour",
        });
        expect(pauseButton.getAttribute("aria-pressed")).toBe("true");
      });
    },
  );
});
