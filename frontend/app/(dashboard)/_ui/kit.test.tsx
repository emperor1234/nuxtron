import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { DataStatus } from "./kit";

describe("DataStatus", () => {
  it("identifies live provider data", () => {
    const html = renderToStaticMarkup(
      <DataStatus state="live" provider="DataForSEO" />,
    );
    expect(html).toContain("Live data");
    expect(html).toContain("DataForSEO");
  });

  it("explains how to activate preview data", () => {
    const html = renderToStaticMarkup(
      <DataStatus state="preview" provider="Similarweb" />,
    );
    expect(html).toContain("Preview data");
    expect(html).toContain("connect Similarweb to activate");
  });

  it("labels unavailable data without inventing a value", () => {
    const html = renderToStaticMarkup(<DataStatus state="unavailable" />);
    expect(html).toContain("Data unavailable");
  });
});
