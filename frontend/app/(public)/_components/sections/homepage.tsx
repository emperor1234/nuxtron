import { HOMEPAGE_ANCHORS } from "@/app/components/marketing/site-links";
import type { HomepageContent } from "../../_content/types";
import { AgentCarouselSection } from "./agent-carousel-section";
import { CapabilityBlocksSection } from "./capability-blocks-section";
import { ClosingSection } from "./closing-section";
import { DemoSection } from "./demo-section";
import { FaqSection } from "./faq-section";
import { HeroSection } from "./hero-section";
import { ProblemSolutionSection } from "./problem-solution-section";
import { ProductHubSection } from "./product-hub-section";
import { ProofCarouselSection } from "./proof-carousel-section";
import { RelatedProductVideo } from "./related-product-video";
import { ResearchGridSection } from "./research-grid-section";
import { TrustBadgesSection } from "./trust-badges-section";
import { UseCaseSection } from "./use-case-section";

/**
 * One homepage, two products. Order: show the product, prove it (proof and
 * trust render nothing until verified entries exist), name the problem, walk
 * through the work, then the detail, the agents and the reading.
 */
export function Homepage({ content }: { content: HomepageContent }) {
  return (
    <>
      <HeroSection content={content.hero} />
      <div id={HOMEPAGE_ANCHORS.demo} className="scroll-mt-24">
        <DemoSection content={content.demo} />
      </div>
      <ProofCarouselSection content={content.proof} />
      <TrustBadgesSection content={content.trust} />
      <ProblemSolutionSection content={content.problemSolution} />
      <RelatedProductVideo product={content.product} />
      <div id={HOMEPAGE_ANCHORS.useCases} className="scroll-mt-24">
        <UseCaseSection content={content.useCases} />
      </div>
      <div id={HOMEPAGE_ANCHORS.capabilities} className="scroll-mt-24">
        <CapabilityBlocksSection content={content.capabilities} product={content.product} />
      </div>
      <div id={HOMEPAGE_ANCHORS.products} className="scroll-mt-24">
        <ProductHubSection content={content.productHub} />
      </div>
      <div id={HOMEPAGE_ANCHORS.agents} className="scroll-mt-24">
        <AgentCarouselSection content={content.agents} />
      </div>
      <div id={HOMEPAGE_ANCHORS.research} className="scroll-mt-24">
        <ResearchGridSection content={content.research} />
      </div>
      <div id={HOMEPAGE_ANCHORS.faq} className="scroll-mt-24">
        <FaqSection items={content.faq} />
      </div>
      <ClosingSection content={content.closing} />
    </>
  );
}
