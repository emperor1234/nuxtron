import { productAuthHref } from "@/app/lib/product-line";
import type { HomepageContent } from "./types";

const START = productAuthHref("/register", "marketing");

/**
 * Nuxtron Marketing homepage. Every capability below maps to a page in the
 * Content, Social or Studio dashboard menus (app/(dashboard)/_shell/nav.ts).
 *
 * Channel coverage lists networks registered in the social workspace
 * (backend/fastapi/app/routers/social_workspace.py, SUPPORTED_NETWORKS). Which
 * ones a workspace can publish to depends on that provider's credentials,
 * which the FAQ says plainly.
 */
export const marketingHomepage: HomepageContent = {
  product: "marketing",

  hero: {
    eyebrow: "Content, social and customer work",
    headlineLead: "Plan it. Make it.",
    headlineAccent: "Ship it everywhere.",
    highlight: "everywhere",
    intro:
      "Nuxtron Marketing brings your content calendar, social channels, creative studio and inbox together, so a brief becomes a published post without changing tools.",
    primaryCta: { label: "Start with Nuxtron Marketing", href: START },
    secondaryCta: { label: "See it working", href: "#demo" },
    explainer: "marketing",
    coverageLabel: "Connect channels including",
    coverage: [
      "Instagram",
      "LinkedIn",
      "Facebook",
      "TikTok",
      "YouTube",
      "X",
      "Pinterest",
      "Threads",
      "Google Business Profile",
      "Bluesky",
    ],
  },

  demo: {
    eyebrow: "Product tour",
    title: "Your marketing workspace, without sample data.",
    intro: "Explore the workspace structure in a sample-free preview. No scheduled content, engagement metrics, connected account data, or customer conversations are shown.",
    disclaimer: "Empty preview states only. Connect authorized channels in your workspace to see real content and metrics.",
    views: [
      {
        id: "calendar",
        label: "Calendar",
        icon: "calendar",
        heading: "Content calendar",
        subheading: "No connected schedule data",
        kpis: [
          { label: "Scheduled", value: "Not loaded" },
          { label: "In review", value: "Not loaded" },
          { label: "Published", value: "Not loaded" },
        ],
        list: {
          label: "Data status",
          rows: [
            { tag: "Schedule", text: "No posts or drafts are included in this preview." },
            { tag: "Source", text: "An authorized channel connection is required for account content." },
            { tag: "Scope", text: "No publish action is available from this public preview." },
          ],
        },
      },
      {
        id: "performance",
        label: "Performance",
        icon: "chart",
        heading: "Channel performance",
        subheading: "No verified analytics loaded",
        kpis: [
          { label: "Engagement", value: "Not available" },
          { label: "Link clicks", value: "Not available" },
          { label: "Audience change", value: "Not available" },
        ],
        list: {
          label: "Data status",
          rows: [
            { tag: "Source", text: "No social analytics provider is connected in this preview." },
            { tag: "Metrics", text: "No engagement or reach figures are estimated." },
            { tag: "Compare", text: "Use verified, comparable periods before drawing conclusions." },
          ],
        },
      },
      {
        id: "inbox",
        label: "Inbox",
        icon: "inbox",
        heading: "Smart inbox",
        subheading: "No connected conversations are shown",
        kpis: [
          { label: "Open conversations", value: "Not loaded" },
          { label: "First reply time", value: "Not calculated" },
          { label: "Assigned", value: "Not loaded" },
        ],
        list: {
          label: "Data status",
          rows: [
            { tag: "Messages", text: "No messages or comments have been loaded." },
            { tag: "Reviews", text: "Review-provider feeds are not currently available." },
            { tag: "Replies", text: "No sample conversations or sent replies are shown." },
          ],
        },
      },
      {
        id: "studio",
        label: "Studio",
        icon: "sparkles",
        heading: "Creative studio",
        subheading: "No generated assets or drafts loaded",
        kpis: [
          { label: "Assets", value: "Not loaded" },
          { label: "Approvals", value: "Not loaded" },
          { label: "Repurposed content", value: "Not loaded" },
        ],
        list: {
          label: "Data status",
          rows: [
            { tag: "Assets", text: "No sample creative assets are included." },
            { tag: "Review", text: "No draft is represented as reviewed or approved." },
            { tag: "Publish", text: "Nothing in this preview is published." },
          ],
        },
      },
    ],
  },

  // Only real, permissioned customer statements with a checkable source may
  // be added here. Until then the proof section renders nothing.
  proof: { eyebrow: "Customers", title: "Teams shipping more with less switching.", entries: [] },

  // Only awards with a public proof URL may be added. Swap in the issuer's
  // official embed once Nuxtron holds one. Until then the row renders nothing.
  trust: { title: "Recognised by", badges: [] },

  problemSolution: {
    eyebrow: "The six-tab problem",
    title: "Good work gets lost between tools.",
    problems: [
      {
        title: "Context goes missing",
        body: "The brief lives in one tool, the draft in another, the schedule in a third. Every hand-off drops a little of why the work exists.",
      },
      {
        title: "Approvals stall",
        body: "Reviews happen in comment threads and chat, so nobody is sure what's approved and posts go out late — or not at all.",
      },
      {
        title: "Replies slip through",
        body: "Comments and messages arrive on every channel separately, and the ones that matter get answered last.",
      },
    ],
    solution: {
      title: "One workspace from brief to published post to reply.",
      body: "Nuxtron Marketing keeps the brief, the creative, the approval and the conversation in the same place, so the work moves and nothing gets lost.",
      cta: { label: "Start with Nuxtron Marketing", href: START },
    },
  },

  useCases: {
    eyebrow: "How teams use it",
    title: "From idea to post to conversation.",
    intro: "A typical campaign in Nuxtron Marketing, start to finish.",
    steps: [
      {
        id: "plan",
        label: "Plan the campaign",
        icon: "calendar",
        title: "Start with a brief, not a blank calendar.",
        body: "Content Brief and the Content Calendar turn a campaign goal into a dated plan across every channel.",
        panel: {
          kind: "rows",
          caption: "Campaign brief",
          items: [
            "Goal: webinar sign-ups from LinkedIn and email",
            "Audience: operations leads at 50–200 person companies",
            "Five posts, one newsletter, one reminder",
            "Publish window: 12–26 October",
          ],
        },
      },
      {
        id: "create",
        label: "Create the assets",
        icon: "sparkles",
        title: "Make every format from one source.",
        body: "The AI Copywriter, AI Image Studio and Content Repurposer turn one piece into the posts, sizes and cuts each channel needs, in your Brand Kit.",
        panel: {
          kind: "rows",
          caption: "Repurposed from the guide",
          items: [
            "LinkedIn carousel · 5 slides",
            "Instagram reel · 30 seconds",
            "Newsletter section · 180 words",
            "X thread · 6 posts",
          ],
        },
      },
      {
        id: "approve",
        label: "Review and schedule",
        icon: "users",
        title: "Approve once, publish everywhere.",
        body: "Content Approvals routes each piece to the right reviewer, and the Post Scheduler publishes at each channel's best time.",
        panel: {
          kind: "bars",
          caption: "Best time to post · relative engagement",
          items: ["Tue 09:00:88", "Wed 12:30:74", "Thu 15:00:61", "Fri 10:00:43"],
        },
      },
      {
        id: "respond",
        label: "Respond and learn",
        icon: "inbox",
        title: "Answer the people who answered you.",
        body: "The Smart Inbox gathers replies from every channel, and Social Media ROI shows which posts earned their place.",
        panel: {
          kind: "answer",
          caption: "Smart inbox",
          items: [
            "Is the webinar recording going to be shared?",
            "Yes — everyone who registers gets the recording within a day. [Saved reply]",
            "You can register from the link in our profile. [LinkedIn]",
          ],
        },
      },
    ],
  },

  capabilities: {
    eyebrow: "What's inside",
    title: "Everything a marketing team ships.",
    intro: "Nine areas, one login. Open any of them to see what's included.",
    blocks: [
      {
        id: "calendar",
        icon: "calendar",
        title: "Content calendar",
        summary: "Plan every channel on one calendar, with briefs attached.",
        bullets: ["Content Calendar", "Content Brief", "Post Scheduler"],
        link: { label: "See all features", href: "/features" },
      },
      {
        id: "writing",
        icon: "file-text",
        title: "Writing",
        summary: "Draft, check and polish copy in your brand voice.",
        bullets: ["AI Copywriter", "On-Page Checker", "Readability Score", "Brand Voice DNA"],
        link: { label: "See all features", href: "/features" },
      },
      {
        id: "creative",
        icon: "sparkles",
        title: "Creative studio",
        summary: "Images, short video and templates, made on brand.",
        bullets: ["Editor", "AI Image Studio", "Short Video Factory", "Template System"],
        link: { label: "See all features", href: "/features" },
      },
      {
        id: "publishing",
        icon: "share",
        title: "Social publishing",
        summary: "Schedule once and publish across your connected channels.",
        bullets: ["Post Scheduler", "Social Scheduling", "Link In Bio", "Content Repurposer"],
        link: { label: "See integrations", href: "/integrations" },
      },
      {
        id: "inbox",
        icon: "inbox",
        title: "Inbox and comments",
        summary: "Reply to comments and messages from one queue.",
        bullets: ["Smart Inbox", "Comment Replies"],
        link: { label: "See all features", href: "/features" },
      },
      {
        id: "brand",
        icon: "shield",
        title: "Brand consistency",
        summary: "Keep every asset and post true to the brand.",
        bullets: ["Brand Hub", "Brand Kit", "Brand Voice DNA"],
        link: { label: "See all features", href: "/features" },
      },
      {
        id: "repurpose",
        icon: "workflow",
        title: "Repurposing",
        summary: "Turn one long piece into posts for every channel.",
        bullets: ["Content Repurposer", "Ideas & Drafts"],
        link: { label: "See all features", href: "/features" },
      },
      {
        id: "analytics",
        icon: "chart",
        title: "Performance",
        summary: "See what each post and channel returned.",
        bullets: ["Platform Analytics", "Social Media ROI", "A/B Testing Engine", "ROI Forecaster"],
        link: { label: "See all features", href: "/features" },
      },
      {
        id: "team",
        icon: "users",
        title: "Team and approvals",
        summary: "Clear owners and sign-off before anything goes live.",
        bullets: ["Content Approvals", "Workspace", "Workflow Automation"],
        link: { label: "See all features", href: "/features" },
      },
    ],
  },

  productHub: {
    eyebrow: "Nuxtron Marketing",
    title: "Three workspaces that share one plan.",
    intro: "Each area of the dashboard has a clear job, and they all work from the same calendar and brand.",
    cards: [
      {
        id: "content",
        icon: "file-text",
        name: "Content",
        tagline: "Plan, brief and write.",
        features: ["Content Calendar", "Content Brief", "AI Copywriter", "Content Repurposer"],
        link: { label: "Start with Content", href: START },
      },
      {
        id: "social",
        icon: "share",
        name: "Social",
        tagline: "Publish, listen and reply.",
        features: ["Post Scheduler", "Smart Inbox", "Social Trends", "Social Media ROI"],
        link: { label: "Start with Social", href: START },
      },
      {
        id: "studio",
        icon: "sparkles",
        name: "Studio",
        tagline: "Make the creative on brand.",
        features: ["AI Image Studio", "Short Video Factory", "Brand Kit", "Content Approvals"],
        link: { label: "Start with Studio", href: START },
      },
    ],
  },

  agents: {
    eyebrow: "AI agents",
    title: "AI tools and automations that keep work moving.",
    intro: "Use workspace data to draft and optimize content, then configure repeatable workflows with explicit triggers and actions.",
    agents: [
      {
        id: "ira",
        name: "IRA",
        role: "Runs the operator hub",
        body: "Your assistant for publishing, trends, the inbox and content generation — with queue controls and a pause-all switch when you need to stop everything.",
        actions: ["Draft from a prompt", "Pause the queue", "Open the right tool"],
        link: { label: "Meet IRA", href: START },
      },
      {
        id: "workflow-automation",
        name: "Workflow Automation",
        role: "Automates configured workspace tasks",
        body: "Create workflows from explicit triggers and steps, then review their status and execution history in your workspace.",
        actions: ["Choose a trigger", "Configure steps", "Review executions"],
        link: { label: "Explore workflows", href: START },
      },
      {
        id: "agent-analytics",
        name: "Agent Analytics",
        role: "Watches the bots",
        body: "Tracks AI crawler and bot traffic to your site in real time, so you can see which assistants are reading your content.",
        actions: ["Track AI crawlers", "Spot new bots", "See what they read"],
        link: { label: "See Agent Analytics", href: START },
      },
    ],
  },

  research: {
    eyebrow: "Research and guides",
    title: "Notes on running marketing without the tab tax.",
    intro: "What we've learned building one workspace for content, social and customer work.",
    cta: { label: "Read the blog", href: "/blog" },
  },

  faq: [
    {
      q: "Which channels can I publish to?",
      a: "The social workspace supports connecting forty networks, including Instagram, LinkedIn, Facebook, TikTok, YouTube, X and Pinterest. Each one publishes once its provider credentials are configured for your workspace — the integrations page lists what's available.",
    },
    {
      q: "Can my team review posts before they go out?",
      a: "Yes. Content Approvals routes social content to reviewers before publishing. Workspace workflows separately automate the triggers and steps you configure.",
    },
    {
      q: "What's the difference between Nuxtron Marketing and Nuxtron SEO?",
      a: "Nuxtron Marketing is for content, social channels and customer work. Nuxtron SEO is for search and AI visibility. You choose one when you sign in, and the dashboard shows that product's tools.",
    },
    {
      q: "How do I choose a plan?",
      a: "The pricing page lists the plans and the usage each includes. Review the limits there before activating a subscription.",
    },
  ],

  closing: {
    eyebrow: "Get started",
    titleLead: "One workspace.",
    titleAccent: "Every channel in step.",
    primaryCta: { label: "Start with Nuxtron Marketing", href: START },
    secondaryCta: { label: "Talk to our team", href: "/contact" },
  },
};
