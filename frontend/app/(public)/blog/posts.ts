export type BlogPost = {
  slug: string;
  title: string;
  description: string;
  date: string;
  author: string;
  readMinutes: number;
  category: string;
  paragraphs: string[];
};

export const BLOG_POSTS: BlogPost[] = [
  {
    slug: 'ai-answer-engines-are-the-new-search-results-page',
    title: 'AI answer engines are the new search results page',
    description:
      'Why tracking keyword rankings alone is no longer enough, and what AEO/GEO visibility actually measures.',
    date: '2026-07-28',
    author: 'Nuxtron Team',
    readMinutes: 6,
    category: 'SEO & AI visibility',
    paragraphs: [
      'For two decades, "search visibility" meant one thing: where a page ranked on a results page you could scroll through. That assumption is breaking down. A growing share of buying research now happens inside a conversation with an AI assistant — ChatGPT, Gemini, Claude, Copilot — where there is no results page, no ten blue links, and no scroll to fight for position twelve.',
      'That shift creates a new, mostly invisible failure mode: a brand can rank well on traditional search and still be functionally absent from how AI models describe its category. We call tracking that gap Answer-Engine Optimization (AEO) and Generative-Engine Optimization (GEO) — measuring whether, and how accurately, AI answer engines cite and represent your brand when someone asks about the problem you solve.',
      'The mechanics are different from classic SEO. Traditional rank tracking answers "where do I appear for this query." AEO/GEO tracking answers three different questions: does the model mention you at all, does it cite you as a source when it does, and is what it says about you accurate. A brand can lose on all three independently — invisible, cited-but-generic, or worst, cited-and-wrong.',
      'What actually moves these numbers looks less like classic link-building and more like structured clarity: canonical pages that state claims plainly and verifiably, schema markup that gives models unambiguous entities to anchor on, and third-party corroboration that lets a model treat a claim as safe to repeat. None of this replaces traditional SEO — it runs alongside it, informed by the same content, judged by a different, less legible audience.',
      'The teams catching this early are the ones treating AI citation tracking as a first-class metric next to rank position and organic traffic — not a curiosity to check once a quarter. If you can\'t currently answer "what does ChatGPT say about us when someone asks about our category," that\'s the gap worth closing first.',
    ],
  },
  {
    slug: 'the-real-cost-of-the-six-tab-tax',
    title: 'The real cost of the six-tab tax',
    description:
      'Running CRM, SEO, social, and security in separate tools does not just cost subscription fees — it costs context.',
    date: '2026-06-14',
    author: 'Nuxtron Team',
    readMinutes: 5,
    category: 'Company',
    paragraphs: [
      'Ask a growth team how many tools they run and you\'ll get a number somewhere between five and nine: a CRM, an SEO platform, a social scheduler, a review manager, a security dashboard, and usually a spreadsheet quietly gluing the gaps between them together. Ask what that costs and most teams will quote the subscription total. That\'s the smaller number.',
      'The larger, harder-to-see cost is context loss. A lead that came in through a social campaign has to be manually re-tagged in the CRM. A keyword ranking drop that correlates with a technical change has to be cross-referenced by a person remembering both dashboards exist. A security alert has no idea what marketing campaign was running when the unusual traffic pattern started. Every handoff between tools is a place institutional knowledge quietly falls on the floor.',
      'This is not an argument against specialized tools in general — a team of one doesn\'t need a unified platform. It\'s an argument about what happens once more than two people touch the same customer data from different tools: the reconciliation tax compounds. Someone spends part of every week just making sure the CRM, the ad platform, and the support tool agree with each other.',
      'The fix isn\'t "use fewer tools" as a slogan — it\'s making sure the tools that do stay share one data model and one tenant, so a contact created from a social DM is the same row a support ticket references and the same row an AI agent can act on. That\'s the actual argument for a connected workspace: not fewer logins, but zero reconciliation.',
    ],
  },
  {
    slug: 'what-supervised-autonomy-means-for-ai-agents',
    title: 'What "supervised autonomy" actually means for AI agents',
    description:
      'Full autonomy and a chatbot that only suggests are both wrong defaults. Here is the middle Nuxtron\'s IRA agent is built on.',
    date: '2026-05-02',
    author: 'Nuxtron Team',
    readMinutes: 7,
    category: 'AI agents',
    paragraphs: [
      'There are two failure modes teams keep running into with AI agents in production tools. The first is an agent that only ever suggests — every action requires a human to re-do the work of reviewing, understanding, and manually executing it, which means the agent saves almost no time. The second is an agent that just acts, silently, at scale, until something goes wrong badly enough that someone finally reads the logs.',
      'Neither is the right default for work that touches customer data, spend, or public-facing content. The useful middle ground is what we call supervised autonomy: an agent that can genuinely execute multi-step work — not just draft a single message — but does so inside explicit, configurable approval gates, with every action logged in a way a human can actually audit after the fact.',
      'Concretely, that means three things have to be true simultaneously. First, actions have to be scoped: an agent working on social scheduling shouldn\'t have an implicit path to CRM data it was never asked to touch. Second, risk has to be tiered: reformatting a draft post and spending ad budget are not the same category of action, and shouldn\'t require the same approval threshold. Third, everything has to be reversible or at minimum fully attributable — "the agent did this, here is exactly what changed and why" has to be answerable in one query, not a forensic exercise.',
      'This is slower to build than either extreme. A pure autopilot is a simpler system to ship. A pure suggestion box requires no trust model at all. Supervised autonomy requires building the trust model first — the approval gates, the audit trail, the scoping — and only then layering the actual automation on top. We think that order is the only one that survives contact with a real customer\'s real data.',
    ],
  },
];

export function getPostBySlug(slug: string): BlogPost | undefined {
  return BLOG_POSTS.find((post) => post.slug === slug);
}
