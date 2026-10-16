import type { Metadata } from "next";
import { SectionHub } from "../../_ui/section-hub";

export const metadata: Metadata = {
  title: "Social · Nuxtron",
  description: "Plan, publish, engage and measure across your connected social accounts.",
};

export default function SocialHomePage() {
  return <SectionHub section="social" />;
}
