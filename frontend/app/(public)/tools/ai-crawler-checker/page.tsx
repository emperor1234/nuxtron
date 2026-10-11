import type { Metadata } from "next";
import { FreeToolFrame } from "../_components/free-tool-frame";
import { AiCrawlerChecker } from "../_components/ai-crawler-checker";

export const metadata: Metadata = {
  title: "AI crawler checker | Free tools | Nuxtron",
  description:
    "Check how common AI crawler user-agent tokens match your robots.txt rules. The analysis runs in your browser.",
  alternates: { canonical: "/tools/ai-crawler-checker" },
};

export default function AiCrawlerCheckerPage() {
  return (
    <FreeToolFrame
      eyebrow="Free AI-search utility"
      title="AI crawler checker"
      description="See how common AI search and assistant crawlers match the rules in a robots.txt file. Paste the file to run a local, sample-path check."
    >
      <AiCrawlerChecker />
    </FreeToolFrame>
  );
}
