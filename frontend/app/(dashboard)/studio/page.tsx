import type { Metadata } from "next";
import { SectionHub } from "../_ui/section-hub";

export const metadata: Metadata = {
  title: "Studio · Nuxtron",
  description: "Create content and manage the brand it follows.",
};

export default function StudioHomePage() {
  return <SectionHub section="studio" />;
}
