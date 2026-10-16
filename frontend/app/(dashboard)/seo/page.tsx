import type { Metadata } from "next";
import { SectionHub } from "../_ui/section-hub";

export const metadata: Metadata = {
  title: "SEO · Nuxtron",
  description: "AI-assisted optimization for classic search and AI answer engines.",
};

export default function SeoHomePage() {
  return <SectionHub section="seo" />;
}
