import { describe, expect, it } from "vitest";
import { getProviderMark, PROVIDER_MARKS } from "./provider-marks";

describe("getProviderMark", () => {
  it.each([
    ["ChatGPT", "chatgpt"],
    ["ChatGPT / AEO citations", "chatgpt"],
    ["Google Business Profile", "google"],
    ["Google AI Overview", "google"],
    ["Brave Search AI", "brave"],
    ["LinkedIn Video", "linkedin"],
    ["X (Twitter)", "x"],
    ["Google Cloud Storage", "googlecloud"],
    ["GPTBot", "chatgpt"],
    ["OAI SearchBot", "chatgpt"],
    ["PerplexityBot", "perplexity"],
    ["ClaudeBot", "claude"],
    ["GeminiBot", "gemini"],
    ["Google-Extended", "google"],
  ])("resolves %s to the %s mark", (label, expected) => {
    expect(getProviderMark(label)?.key).toBe(expected);
  });

  it("returns no mark for labels that are not a known provider", () => {
    expect(getProviderMark("SAML SSO")).toBeUndefined();
    expect(getProviderMark("")).toBeUndefined();
  });

  it("uses only locally hosted asset paths", () => {
    expect(PROVIDER_MARKS.length).toBeGreaterThan(20);
    for (const mark of PROVIDER_MARKS) {
      expect(mark.src).toMatch(/^\/brand\/providers\//);
    }
  });
});
