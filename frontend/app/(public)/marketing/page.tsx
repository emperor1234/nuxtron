import type { Metadata } from "next";
import { marketingHomepage } from "../_content/marketing";
import { Homepage } from "../_components/sections/homepage";

export const metadata: Metadata = {
  title: "Nuxtron Marketing — Content, social and customer work in one place",
  description:
    "Plan the calendar, make the creative, publish across your channels and answer every reply from one marketing workspace.",
  alternates: { canonical: "/marketing" },
};

export default function MarketingHomePage() {
  return <Homepage content={marketingHomepage} />;
}
