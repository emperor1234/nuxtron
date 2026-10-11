/**
 * Content contract for the two public homepages (`/` for SEO, `/marketing`
 * for Marketing). Every homepage section is a component that takes one of
 * these shapes as its `content` prop, so both products share one set of
 * sections and differ only in data.
 *
 * Honesty rules, enforced by types where possible and by the components at
 * runtime:
 *  - Proof and trust entries must carry `verified: true` and a `source` or
 *    `url` someone can check. Their sections render nothing when the list is
 *    empty — never placeholder quotes, logos, ratings or award badges.
 *  - Product shots use a generic customer account and never
 *    present a number as a result customers should expect.
 *  - Links point at routes that exist. Public CTAs go to public pages or to
 *    `/register?product=…`; dashboard routes require sign-in.
 */

import type { ProductLine } from "@/app/lib/product-line";

export type Cta = { label: string; href: string };

/** Icon names the sections map to lucide-react components. */
export type SectionIcon =
  | "search"
  | "sparkles"
  | "chart"
  | "map-pin"
  | "file-text"
  | "share"
  | "calendar"
  | "users"
  | "workflow"
  | "shield"
  | "megaphone"
  | "inbox"
  | "bot"
  | "link";

export type HeroContent = {
  eyebrow: string;
  /** First headline line, ink colour. */
  headlineLead: string;
  /** Second headline line, brand colour. */
  headlineAccent: string;
  /** One word from either headline line to mark with a highlighter sweep. */
  highlight?: string;
  intro: string;
  primaryCta: Cta;
  secondaryCta: Cta;
  /** Named engines (SEO) or channels (Marketing) shown under the CTAs. */
  coverageLabel: string;
  coverage: readonly string[];
  /** Which animated product story plays under the hero. */
  explainer?: "seo" | "marketing";
};

export type ProblemSolutionContent = {
  eyebrow: string;
  title: string;
  /** Exactly three pain points read best. */
  problems: readonly { title: string; body: string }[];
  solution: { title: string; body: string; cta: Cta };
};

/** One step of the timed, animated use-case walkthrough. */
export type UseCaseStep = {
  id: string;
  /** Tab label. */
  label: string;
  icon: SectionIcon;
  title: string;
  body: string;
  /** What the staged UI panel shows for this step. */
  panel: {
    kind: "rows" | "bars" | "answer";
    caption: string;
    /** Rows/answer: lines of text. Bars: "Label:value" pairs, value 0–100. */
    items: readonly string[];
  };
};

export type UseCaseContent = {
  eyebrow: string;
  title: string;
  intro: string;
  steps: readonly UseCaseStep[];
};

/** One clickable view in the interactive product demo. */
export type DemoView = {
  id: string;
  label: string;
  icon: SectionIcon;
  heading: string;
  subheading: string;
  kpis: readonly { label: string; value: string; delta?: string }[];
  chart?: { label: string; bars: readonly { label: string; value: number }[] };
  list?: { label: string; rows: readonly { tag: string; text: string }[] };
};

export type DemoContent = {
  eyebrow: string;
  title: string;
  intro: string;
  /** Optional note shown on the demo surface. */
  disclaimer?: string;
  views: readonly DemoView[];
};

export type CapabilityBlock = {
  id: string;
  icon: SectionIcon;
  title: string;
  summary: string;
  /** Revealed when the block is expanded. */
  bullets: readonly string[];
  link: Cta;
};

export type CapabilityContent = {
  eyebrow: string;
  title: string;
  intro: string;
  blocks: readonly CapabilityBlock[];
};

export type ProductHubCard = {
  id: string;
  icon: SectionIcon;
  name: string;
  tagline: string;
  features: readonly string[];
  link: Cta;
};

export type ProductHubContent = {
  eyebrow: string;
  title: string;
  intro: string;
  cards: readonly ProductHubCard[];
};

/** An AI agent that exists in the product today. */
export type AgentCard = {
  id: string;
  name: string;
  role: string;
  body: string;
  /** Short verbs-first examples of what it does. */
  actions: readonly string[];
  link: Cta;
};

export type AgentContent = {
  eyebrow: string;
  title: string;
  intro: string;
  agents: readonly AgentCard[];
};

export type ProofEntry = {
  id: string;
  quote: string;
  person: string;
  role: string;
  company: string;
  metric?: { value: string; label: string };
  /** Must be literally `true`: only real, permissioned customer statements. */
  verified: true;
  /** Where the quote and metric can be checked (case study URL, signed release). */
  source: string;
};

export type ProofContent = {
  eyebrow: string;
  title: string;
  entries: readonly ProofEntry[];
};

export type TrustBadge = {
  id: string;
  /** e.g. "Leader", "High Performer". */
  name: string;
  issuer: string;
  /** e.g. "Fall 2026". */
  season: string;
  /** Public page proving the award. */
  url: string;
  verified: true;
};

export type TrustContent = {
  title: string;
  badges: readonly TrustBadge[];
};

export type ResearchContent = {
  eyebrow: string;
  title: string;
  intro: string;
  /** Category filter applied to BLOG_POSTS; omit to show the latest posts. */
  categories?: readonly string[];
  cta: Cta;
};

export type FaqItem = { q: string; a: string };

export type ClosingContent = {
  eyebrow: string;
  titleLead: string;
  titleAccent: string;
  primaryCta: Cta;
  secondaryCta: Cta;
};

export type HomepageContent = {
  product: ProductLine;
  hero: HeroContent;
  demo: DemoContent;
  proof: ProofContent;
  trust: TrustContent;
  problemSolution: ProblemSolutionContent;
  useCases: UseCaseContent;
  capabilities: CapabilityContent;
  productHub: ProductHubContent;
  agents: AgentContent;
  research: ResearchContent;
  faq: readonly FaqItem[];
  closing: ClosingContent;
};
