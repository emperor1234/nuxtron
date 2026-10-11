/**
 * Public site navigation — the single source of truth for the marketing
 * header, mega menu, mobile drawer and footer.
 *
 * Every href here points at a route that exists under `app/(public)` (or at
 * a section anchor on one of the two product homepages). Dashboard routes are
 * deliberately absent: they require sign-in, so public pages send visitors to
 * `/login` or `/register` with their product choice instead.
 */

import type { LucideIcon } from "lucide-react";
import {
  BadgeCheck,
  Bot,
  Briefcase,
  Building2,
  CalendarRange,
  FileText,
  HelpCircle,
  History,
  Languages,
  KeyRound,
  Radar,
  LayoutGrid,
  Mail,
  MonitorPlay,
  Newspaper,
  Plug,
  Route as RouteIcon,
  Search,
  ScrollText,
  Share2,
  ShieldCheck,
  Sparkles,
  Users,
} from "lucide-react";
import {
  PRODUCT_META,
  productAuthHref,
  type ProductLine,
} from "@/app/lib/product-line";

export type SiteLink = {
  label: string;
  href: string;
  /** One short line shown in the mega menu; never shown in the footer. */
  description?: string;
  icon?: LucideIcon;
};

export type SiteLinkGroup = {
  /** Stable key for React and for accordion ids. */
  id: string;
  title: string;
  /** Optional one-line context under the group title. */
  caption?: string;
  links: readonly SiteLink[];
};

/** A post summary for the Resources menu, computed on the server. */
export type FeaturedPost = {
  slug: string;
  title: string;
  description: string;
  category: string;
  date: string;
  readMinutes: number;
};

/**
 * Section ids the homepage composer should put on each section so the menus
 * can deep-link into both product homepages. Shared by `/` and `/marketing`.
 */
export const HOMEPAGE_ANCHORS = {
  demo: "demo",
  useCases: "use-cases",
  capabilities: "capabilities",
  products: "products",
  agents: "agents",
  research: "research",
  faq: "faq",
} as const;

export type HomepageAnchor =
  (typeof HOMEPAGE_ANCHORS)[keyof typeof HOMEPAGE_ANCHORS];

/** `/#demo` or `/marketing#demo`. */
export function homepageAnchor(
  product: ProductLine,
  anchor: HomepageAnchor,
): string {
  const home = PRODUCT_META[product].homePath;
  return home === "/" ? `/#${anchor}` : `${home}#${anchor}`;
}

function productLinks(product: ProductLine): readonly SiteLink[] {
  const isSeo = product === "seo";
  return [
    {
      label: "Overview",
      href: PRODUCT_META[product].homePath,
      description: PRODUCT_META[product].tagline,
      icon: isSeo ? Search : Share2,
    },
    {
      label: "Interactive demo",
      href: homepageAnchor(product, HOMEPAGE_ANCHORS.demo),
      description: isSeo
        ? "Click through the visibility dashboard."
        : "Click through a week of content.",
      icon: MonitorPlay,
    },
    {
      label: "Capabilities",
      href: homepageAnchor(product, HOMEPAGE_ANCHORS.capabilities),
      description: isSeo
        ? "Audits, rank tracking, backlinks and AI answers."
        : "Content, social publishing and customer work.",
      icon: LayoutGrid,
    },
    {
      label: "AI agents",
      href: homepageAnchor(product, HOMEPAGE_ANCHORS.agents),
      description: isSeo
        ? "Agents that plan the work and review pages."
        : "Agents that run the hub and guard automation.",
      icon: Bot,
    },
  ];
}

export const SEO_GROUP: SiteLinkGroup = {
  id: "seo",
  title: PRODUCT_META.seo.name,
  caption: PRODUCT_META.seo.tagline,
  links: productLinks("seo"),
};

export const MARKETING_GROUP: SiteLinkGroup = {
  id: "marketing",
  title: PRODUCT_META.marketing.name,
  caption: PRODUCT_META.marketing.tagline,
  links: productLinks("marketing"),
};

/** Shared platform pages listed under both products. */
export const PLATFORM_SHARED_LINKS: readonly SiteLink[] = [
  { label: "All features", href: "/features", icon: Sparkles },
  { label: "Integrations", href: "/integrations", icon: Plug },
];

export const SOLUTIONS_GROUP: SiteLinkGroup = {
  id: "solutions",
  title: "By team",
  links: [
    {
      label: "SEO teams",
      href: homepageAnchor("seo", HOMEPAGE_ANCHORS.useCases),
      description: "Find gaps in search and AI answers, then close them.",
      icon: Search,
    },
    {
      label: "Content teams",
      href: homepageAnchor("marketing", HOMEPAGE_ANCHORS.capabilities),
      description: "Turn research into briefs, drafts and assets.",
      icon: FileText,
    },
    {
      label: "Social teams",
      href: homepageAnchor("marketing", HOMEPAGE_ANCHORS.useCases),
      description: "Plan the calendar and keep up with replies.",
      icon: CalendarRange,
    },
    {
      label: "Revenue and CRM",
      href: "/features",
      description: "Keep contacts, deals and campaigns on one record.",
      icon: Users,
    },
    {
      label: "Security and IT review",
      href: "/trust",
      description: "Access controls, audit trails and data handling.",
      icon: ShieldCheck,
    },
    {
      label: "Compare plans",
      href: "/pricing",
      description: "See what each plan includes before you start.",
      icon: RouteIcon,
    },
  ],
};

/** Free tools with shipped, standalone destinations. */
export const FREE_TOOLS_GROUP: SiteLinkGroup = {
  id: "free-tools",
  title: "Free tools",
  caption: "Local checks plus workspace tools.",
  links: [
    {
      label: "AI crawler checker",
      href: "/tools/ai-crawler-checker",
      description: "Available now — inspect robots.txt rules for AI crawlers.",
      icon: Radar,
    },
    {
      label: "Agent permission matrix",
      href: "/tools/agent-permission-matrix",
      description: "Available now — map scoped access and approvals.",
      icon: ShieldCheck,
    },
    {
      label: "MCP security scanner",
      href: "/tools/mcp-security-scanner",
      description: "Available now — review a configuration locally.",
      icon: KeyRound,
    },
    {
      label: "Agent audit-log simulator",
      href: "/tools/agent-audit-log-simulator",
      description: "Available now — walk through approval and audit events.",
      icon: ScrollText,
    },
    {
      label: "Translation Studio",
      href: "/tools/translation-studio",
      description: "Available now — translate and localize copy.",
      icon: Languages,
    },
    {
      label: "All free tools",
      href: "/tools",
      description: "Everything we offer for free, in one place.",
      icon: Sparkles,
    },
  ],
};

export const RESOURCES_GROUP: SiteLinkGroup = {
  id: "resources",
  title: "Learn",
  links: [
    {
      label: "Blog",
      href: "/blog",
      description: "Notes on search, AI answers and marketing work.",
      icon: Newspaper,
    },
    {
      label: "Case studies",
      href: "/case-studies",
      description: "How teams put Nuxtron to work.",
      icon: BadgeCheck,
    },
    {
      label: "Changelog",
      href: "/changelog",
      description: "What shipped, and when.",
      icon: History,
    },
    {
      label: "FAQ",
      href: "/faq",
      description: "Answers on plans, data and setup.",
      icon: HelpCircle,
    },
    {
      label: "Translation Studio",
      href: "/tools/translation-studio",
      description: "A free tool. No account needed.",
      icon: Languages,
    },
  ],
};

export const COMPANY_GROUP: SiteLinkGroup = {
  id: "company",
  title: "Company",
  links: [
    {
      label: "About",
      href: "/about",
      description: "Why we are building Nuxtron.",
      icon: Building2,
    },
    {
      label: "Careers",
      href: "/careers",
      description: "Open roles on the team.",
      icon: Briefcase,
    },
    {
      label: "Contact",
      href: "/contact",
      description: "Talk to sales or support.",
      icon: Mail,
    },
    {
      label: "Trust",
      href: "/trust",
      description: "Security, privacy and compliance.",
      icon: ShieldCheck,
    },
  ],
};

export const PRICING_LINK: SiteLink = { label: "Pricing", href: "/pricing" };

/** Top-level menus, in display order. Pricing sits between Resources and Company. */
export type MenuKey =
  | "platform"
  | "solutions"
  | "tools"
  | "resources"
  | "company";

export const MENU_LABELS: Readonly<Record<MenuKey, string>> = {
  platform: "Platform",
  solutions: "Solutions",
  tools: "Free tools",
  resources: "Resources",
  company: "Company",
};

/** Groups shown for each menu in the mobile drawer accordion. */
export const MOBILE_MENU_GROUPS: Readonly<
  Record<MenuKey, readonly SiteLinkGroup[]>
> = {
  platform: [
    SEO_GROUP,
    MARKETING_GROUP,
    {
      id: "platform-shared",
      title: "Across both products",
      links: PLATFORM_SHARED_LINKS,
    },
  ],
  solutions: [SOLUTIONS_GROUP],
  tools: [FREE_TOOLS_GROUP],
  resources: [RESOURCES_GROUP],
  company: [COMPANY_GROUP],
};

// ---------------------------------------------------------------------------
// Footer
// ---------------------------------------------------------------------------

function footerProductColumn(product: ProductLine): SiteLinkGroup {
  return {
    id: `footer-${product}`,
    title: PRODUCT_META[product].name,
    links: [
      { label: "Overview", href: PRODUCT_META[product].homePath },
      {
        label: "Interactive demo",
        href: homepageAnchor(product, HOMEPAGE_ANCHORS.demo),
      },
      {
        label: "Capabilities",
        href: homepageAnchor(product, HOMEPAGE_ANCHORS.capabilities),
      },
      {
        label: "Use cases",
        href: homepageAnchor(product, HOMEPAGE_ANCHORS.useCases),
      },
      {
        label: "AI agents",
        href: homepageAnchor(product, HOMEPAGE_ANCHORS.agents),
      },
      { label: "Start free", href: productAuthHref("/register", product) },
      {
        label: `Log in to ${PRODUCT_META[product].label}`,
        href: productAuthHref("/login", product),
      },
    ],
  };
}

export const FOOTER_COLUMNS: readonly SiteLinkGroup[] = [
  footerProductColumn("seo"),
  footerProductColumn("marketing"),
  {
    id: "footer-resources",
    title: "Resources",
    links: [
      { label: "Blog", href: "/blog" },
      { label: "Case studies", href: "/case-studies" },
      { label: "Changelog", href: "/changelog" },
      { label: "FAQ", href: "/faq" },
      { label: "Free tools", href: "/tools" },
      { label: "All features", href: "/features" },
      { label: "Integrations", href: "/integrations" },
    ],
  },
  {
    id: "footer-company",
    title: "Company",
    links: [
      { label: "About", href: "/about" },
      { label: "Careers", href: "/careers" },
      { label: "Contact", href: "/contact" },
      { label: "Pricing", href: "/pricing" },
    ],
  },
  {
    id: "footer-legal",
    title: "Legal",
    links: [
      { label: "Privacy policy", href: "/privacy" },
      { label: "Terms of service", href: "/terms" },
      { label: "Trust and security", href: "/trust" },
    ],
  },
];

export const FOOTER_LEGAL_LINKS: readonly SiteLink[] = [
  { label: "Privacy", href: "/privacy" },
  { label: "Terms", href: "/terms" },
  { label: "Trust", href: "/trust" },
];
