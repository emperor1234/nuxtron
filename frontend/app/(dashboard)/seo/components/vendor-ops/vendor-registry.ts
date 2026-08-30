export type VendorOpsView = 'readiness' | 'integrations' | 'automation' | 'assist';

export type VendorSpec = {
  slug: string;
  apiSlug: string;
  label: string;
  website: string;
  views: readonly VendorOpsView[];
  sharedViews: readonly VendorOpsView[];
  defaultKeyword: string;
  defaultCompetitors: readonly string[];
  supportsWiring: boolean;
  supportsProjects: boolean;
  supportsFullAutomation: boolean;
};

const vendor = (
  slug: string,
  label: string,
  website: string,
  views: readonly VendorOpsView[],
  defaultCompetitors: readonly string[] = [],
  options: Partial<
    Pick<
      VendorSpec,
      'apiSlug' | 'sharedViews' | 'supportsWiring' | 'supportsProjects' | 'supportsFullAutomation'
    >
  > = {}
): VendorSpec => ({
  slug,
  apiSlug: options.apiSlug ?? slug,
  label,
  website,
  views,
  sharedViews: options.sharedViews ?? views,
  defaultKeyword: `${label} integration`,
  defaultCompetitors,
  supportsWiring: options.supportsWiring ?? true,
  supportsProjects: options.supportsProjects ?? true,
  supportsFullAutomation: options.supportsFullAutomation ?? true,
});

export const VENDOR_REGISTRY = {
  geoptie: vendor('geoptie', 'Geoptie', 'geoptie.com', ['readiness', 'integrations', 'automation', 'assist'], [
    'writesonic.com',
  ]),
  yext: vendor('yext', 'Yext', 'yext.com', ['readiness', 'integrations', 'automation', 'assist']),
  writesonic: vendor(
    'writesonic',
    'Writesonic',
    'writesonic.com',
    ['readiness', 'integrations', 'automation', 'assist'],
    [],
    { sharedViews: ['readiness', 'integrations', 'assist'] }
  ),
  promptwatch: vendor('promptwatch', 'Promptwatch', 'promptwatch.com', [
    'readiness',
    'integrations',
    'automation',
    'assist',
  ]),
  brightedge: vendor('brightedge', 'BrightEdge', 'brightedge.com', [
    'readiness',
    'integrations',
    'automation',
    'assist',
  ]),
  botify: vendor(
    'botify',
    'Botify',
    'botify.com',
    ['readiness', 'integrations', 'automation', 'assist'],
    [],
    { supportsWiring: false, supportsFullAutomation: false }
  ),
  'seo-ai': vendor(
    'seo-ai',
    'SEO.AI',
    'seo.ai',
    ['readiness', 'integrations', 'automation', 'assist'],
    [],
    { apiSlug: 'seoai', supportsFullAutomation: false }
  ),
  hootsuite: vendor(
    'hootsuite',
    'Hootsuite',
    'hootsuite.com',
    ['readiness', 'integrations', 'automation'],
    [],
    { sharedViews: [] }
  ),
  surfer: vendor('surfer', 'Surfer', 'surferseo.com', ['readiness', 'automation'], [], {
    supportsWiring: false,
    supportsProjects: false,
    supportsFullAutomation: false,
  }),
  semrush: vendor('semrush', 'Semrush', 'semrush.com', [], [], {
    supportsWiring: false,
    supportsProjects: false,
    supportsFullAutomation: false,
  }),
  ahrefs: vendor('ahrefs', 'Ahrefs', 'ahrefs.com', [], [], {
    supportsWiring: false,
    supportsProjects: false,
    supportsFullAutomation: false,
  }),
} as const satisfies Record<string, VendorSpec>;

export type VendorSlug = keyof typeof VENDOR_REGISTRY;

export function vendorSpec(slug: VendorSlug): VendorSpec {
  return VENDOR_REGISTRY[slug];
}
