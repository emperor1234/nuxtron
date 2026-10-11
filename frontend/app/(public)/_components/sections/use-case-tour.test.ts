import { describe, expect, it } from "vitest";
import {
  initialTourState,
  parseAnswerItems,
  parseBarItem,
  tourControl,
  tourReducer,
  type TourAction,
  type TourState,
} from "./use-case-tour";

const COUNT = 4;

function run(actions: TourAction[], from: TourState = initialTourState): TourState {
  return actions.reduce(tourReducer, from);
}

describe("parseBarItem", () => {
  it("parses a label and integer value", () => {
    expect(parseBarItem("Search visibility:72")).toEqual({ label: "Search visibility", value: 72 });
  });

  it("splits on the last colon so labels may contain one", () => {
    expect(parseBarItem("Engine: answer share:40")).toEqual({ label: "Engine: answer share", value: 40 });
  });

  it("trims whitespace and rounds decimals", () => {
    expect(parseBarItem("  Local : 33.6 ")).toEqual({ label: "Local", value: 34 });
  });

  it("clamps out-of-range values into 0–100", () => {
    expect(parseBarItem("High:140")?.value).toBe(100);
    expect(parseBarItem("Low:-5")?.value).toBe(0);
  });

  it("rejects malformed items", () => {
    expect(parseBarItem("No value")).toBeNull();
    expect(parseBarItem(":50")).toBeNull();
    expect(parseBarItem("Label:")).toBeNull();
    expect(parseBarItem("Label:abc")).toBeNull();
    expect(parseBarItem("Label:5O")).toBeNull();
  });
});

describe("parseAnswerItems", () => {
  it("treats the first item as the question and the rest as lines", () => {
    const parsed = parseAnswerItems(["Which tools track AI answers?", "Line one", "Line two"]);
    expect(parsed.question).toBe("Which tools track AI answers?");
    expect(parsed.lines).toEqual([
      { text: "Line one", source: null },
      { text: "Line two", source: null },
    ]);
  });

  it("lifts a trailing [source] into a citation", () => {
    expect(parseAnswerItems(["Q", "Brand is cited first [Product docs]"]).lines).toEqual([
      { text: "Brand is cited first", source: "Product docs" },
    ]);
  });

  it("drops empty lines and survives an empty list", () => {
    expect(parseAnswerItems(["Q", "  "]).lines).toEqual([]);
    expect(parseAnswerItems([])).toEqual({ question: "", lines: [] });
  });
});

describe("tourReducer", () => {
  it("starts only from idle", () => {
    expect(run([{ type: "start", count: COUNT }]).status).toBe("playing");
    const stopped = run([{ type: "select", index: 2, animate: true }]);
    expect(tourReducer(stopped, { type: "start", count: COUNT })).toBe(stopped);
  });

  it("advances once through the steps and stops on the last one", () => {
    const ticks: TourAction[] = Array.from({ length: 10 }, () => ({ type: "tick", count: COUNT }));
    const states = ticks.reduce<TourState[]>(
      (acc, action) => [...acc, tourReducer(acc[acc.length - 1]!, action)],
      [run([{ type: "start", count: COUNT }])],
    );
    expect(states.map((s) => s.index).slice(0, 5)).toEqual([0, 1, 2, 3, 3]);
    expect(states[3]!.status).toBe("done");
    expect(states[states.length - 1]).toEqual(states[3]);
  });

  it("ignores ticks while paused and resumes on the same step", () => {
    const paused = run([
      { type: "start", count: COUNT },
      { type: "tick", count: COUNT },
      { type: "pause" },
      { type: "tick", count: COUNT },
    ]);
    expect(paused).toMatchObject({ index: 1, status: "paused" });
    expect(tourReducer(paused, { type: "resume" })).toMatchObject({ index: 1, status: "playing" });
  });

  it("stops permanently when the viewer picks a tab", () => {
    const state = run([
      { type: "start", count: COUNT },
      { type: "select", index: 2, animate: false },
      { type: "tick", count: COUNT },
      { type: "resume" },
      { type: "start", count: COUNT },
    ]);
    expect(state).toMatchObject({ index: 2, status: "stopped", animate: false });
  });

  it("replays from the first step with a new run id", () => {
    const done = run([
      { type: "start", count: 2 },
      { type: "tick", count: 2 },
    ]);
    expect(done.status).toBe("done");
    const replayed = tourReducer(done, { type: "replay", count: 2 });
    expect(replayed).toMatchObject({ index: 0, status: "playing", run: done.run + 1 });
  });

  it("finishes immediately when there is a single step", () => {
    expect(run([{ type: "start", count: 1 }]).status).toBe("done");
    expect(run([{ type: "replay", count: 1 }]).status).toBe("done");
  });

  it("stop (reduced motion) halts a running or pending tour only", () => {
    expect(run([{ type: "stop" }]).status).toBe("stopped");
    expect(run([{ type: "start", count: COUNT }, { type: "stop" }]).status).toBe("stopped");
    const done = run([{ type: "start", count: 1 }]);
    expect(tourReducer(done, { type: "stop" })).toBe(done);
  });
});

describe("tourControl", () => {
  it("maps every status to one control", () => {
    expect(tourControl("idle")).toBe("play");
    expect(tourControl("playing")).toBe("pause");
    expect(tourControl("paused")).toBe("resume");
    expect(tourControl("done")).toBe("replay");
    expect(tourControl("stopped")).toBe("replay");
  });
});
