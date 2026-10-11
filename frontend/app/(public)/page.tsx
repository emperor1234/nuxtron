import type { Metadata } from "next";
import { seoHomepage } from "./_content/seo";
import { Homepage } from "./_components/sections/homepage";

export const metadata: Metadata = {
  title: "Nuxtron SEO — Search and AI answer-engine visibility",
  description:
    "Track how your brand ranks in search and how ChatGPT, Perplexity, Gemini and Claude describe it, then fix, write and build what moves it.",
  alternates: { canonical: "/" },
};

export default function SeoHomePage() {
  return <Homepage content={seoHomepage} />;
}
