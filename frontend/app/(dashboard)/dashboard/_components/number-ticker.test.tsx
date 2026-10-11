import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import NumberTicker from "./number-ticker";

const { animateMock, useInViewMock, useReducedMotionMock } = vi.hoisted(() => ({
  animateMock: vi.fn(),
  useInViewMock: vi.fn(),
  useReducedMotionMock: vi.fn(),
}));

vi.mock("framer-motion", () => ({
  animate: animateMock,
  useInView: useInViewMock,
  useReducedMotion: useReducedMotionMock,
}));

afterEach(cleanup);
beforeEach(() => {
  vi.clearAllMocks();
  useInViewMock.mockReturnValue(true);
  useReducedMotionMock.mockReturnValue(false);
  animateMock.mockReturnValue({ stop: vi.fn() });
});

describe("NumberTicker", () => {
  it("uses the short default duration and shared ease-out curve", async () => {
    render(<NumberTicker value={42} />);

    await waitFor(() => expect(animateMock).toHaveBeenCalledTimes(1));
    expect(animateMock).toHaveBeenCalledWith(
      0,
      42,
      expect.objectContaining({
        duration: 0.2,
        ease: [0.23, 1, 0.32, 1],
      }),
    );
  });

  it("renders the final formatted value without animation for reduced motion", async () => {
    useReducedMotionMock.mockReturnValue(true);
    render(<NumberTicker value={1234} prefix="$" />);

    await waitFor(() => expect(screen.getByText("$1,234")).toBeTruthy());
    expect(animateMock).not.toHaveBeenCalled();
  });
});
