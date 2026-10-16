import { SeoToolPage } from "../_tool/tool-page";
import { SEO_TOOLS } from "../_tool/specs";

export default function Page() {
  return <SeoToolPage spec={SEO_TOOLS["agent"]} />;
}
