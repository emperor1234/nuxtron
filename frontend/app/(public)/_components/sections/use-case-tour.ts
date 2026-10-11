/**
 * Pure state and parsing helpers for the use-case walkthrough. Kept free of
 * React and the DOM so every transition the tour can make is unit-tested.
 */

/** How long each step stays on screen while the tour auto-advances. */
export const USE_CASE_STEP_MS = 4000;

export type BarDatum = { label: string; value: number };

/**
 * Parses a bars-panel item of the form "Label:value" (value 0–100).
 * Splits on the last colon so labels may contain colons; clamps the value.
 *
 * @returns the label and clamped value, or null when the item is malformed.
 */
export function parseBarItem(item: string): BarDatum | null {
  const separator = item.lastIndexOf(":");
  if (separator <= 0) return null;
  const label = item.slice(0, separator).trim();
  const raw = item.slice(separator + 1).trim();
  if (!label || !/^-?\d+(?:\.\d+)?$/.test(raw)) return null;
  const value = Math.min(100, Math.max(0, Math.round(Number(raw))));
  return { label, value };
}

export type AnswerLine = { text: string; source: string | null };

/**
 * Splits an answer-panel item list into the prompt and the answer lines.
 * A line may end with "[Source name]", which becomes its citation chip.
 *
 * @returns the question (first item) and the remaining lines.
 */
export function parseAnswerItems(items: readonly string[]): {
  question: string;
  lines: AnswerLine[];
} {
  const [question = "", ...rest] = items;
  const lines = rest
    .map((line) => {
      const match = /^(.*?)\s*\[([^\]]+)\]\s*$/.exec(line);
      if (match && match[1]) {
        return { text: match[1].trim(), source: match[2]!.trim() };
      }
      return { text: line.trim(), source: null };
    })
    .filter((line) => line.text.length > 0);
  return { question: question.trim(), lines };
}

/**
 * idle     – not yet seen; waiting for the section to scroll into view.
 * playing  – counting down the active step.
 * paused   – the viewer paused; the countdown keeps its elapsed time.
 * done     – reached the last step on its own.
 * stopped  – the viewer took over (picked a tab) or asked for reduced motion.
 *            Nothing restarts the tour except an explicit replay.
 */
export type TourStatus = "idle" | "playing" | "paused" | "done" | "stopped";

export type TourState = {
  index: number;
  status: TourStatus;
  /** Bumped on every replay so the progress track and panel restart. */
  run: number;
  /** Whether the next panel change should play its entrance sequence. */
  animate: boolean;
};

export type TourAction =
  | { type: "start"; count: number }
  | { type: "tick"; count: number }
  | { type: "pause" }
  | { type: "resume" }
  | { type: "replay"; count: number }
  | { type: "select"; index: number; animate: boolean }
  | { type: "stop" };

export const initialTourState: TourState = {
  index: 0,
  status: "idle",
  run: 0,
  animate: false,
};

/** Status after landing on `index`: a tour stops by itself on its last step. */
function statusAt(index: number, count: number): TourStatus {
  return index >= count - 1 ? "done" : "playing";
}

/** Every state change of the walkthrough. Unknown or invalid moves are no-ops. */
export function tourReducer(state: TourState, action: TourAction): TourState {
  switch (action.type) {
    case "start":
      if (state.status !== "idle") return state;
      return { ...state, status: statusAt(state.index, action.count) };
    case "tick": {
      if (state.status !== "playing") return state;
      const index = Math.min(state.index + 1, Math.max(action.count - 1, 0));
      return { ...state, index, status: statusAt(index, action.count), animate: true };
    }
    case "pause":
      return state.status === "playing" ? { ...state, status: "paused" } : state;
    case "resume":
      return state.status === "paused" ? { ...state, status: "playing" } : state;
    case "replay":
      return {
        index: 0,
        status: statusAt(0, action.count),
        run: state.run + 1,
        animate: true,
      };
    case "select":
      return { ...state, index: action.index, status: "stopped", animate: action.animate };
    case "stop":
      return state.status === "playing" || state.status === "paused" || state.status === "idle"
        ? { ...state, status: "stopped" }
        : state;
    default:
      return state;
  }
}

export type TourControl = "play" | "pause" | "resume" | "replay";

/** The single control the viewer gets, derived from the tour status. */
export function tourControl(status: TourStatus): TourControl {
  if (status === "idle") return "play";
  if (status === "playing") return "pause";
  if (status === "paused") return "resume";
  return "replay";
}
