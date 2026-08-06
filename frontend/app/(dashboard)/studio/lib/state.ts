/**
 * Zustand store for Nuxtron Studio state management.
 * Consolidates 61+ demo outputs and control state into a single source of truth.
 * Production-safe: state serializable and immutable-friendly.
 */
import { create } from 'zustand';

type AnyObject = Record<string, unknown>;

const DEFAULT_STUDIO_TENANT_ID = (process.env.NEXT_PUBLIC_DEFAULT_TENANT_ID || '').trim();

export interface StudioState {
  // ── Control State ─────────────────────────────────────────
  apiKey: string;
  tenantId: string;
  publishAt: string;
  globalError: string;
  contentError: string;
  isGeneratingContent: boolean;
  latestTotpSecret: string;
  latestJwtToken: string;

  // ── Demo Outputs (by category) ───────────────────────────
  outputs: {
    content: AnyObject | null;
    ads: AnyObject | null;
    seo: AnyObject | null;
    social: AnyObject | null;
    listening: AnyObject | null;
    listeningAlerts: AnyObject | null;
    listeningClusters: AnyObject | null;
    reviews: AnyObject | null;
    suitecrm: AnyObject | null;
    refferq: AnyObject | null;
    posthog: AnyObject | null;
    matomo: AnyObject | null;
    plausible: AnyObject | null;
    n8n: AnyObject | null;
    growthbook: AnyObject | null;
    ops: AnyObject | null;
    metrics: AnyObject | null;
    searchIndex: AnyObject | null;
    searchQuery: AnyObject | null;
    webhook: AnyObject | null;
    webhookEvents: AnyObject | null;
    appwriteUser: AnyObject | null;
    appwriteSession: AnyObject | null;
    drone: AnyObject | null;
    directusCreate: AnyObject | null;
    directusList: AnyObject | null;
    minioPresign: AnyObject | null;
    minioList: AnyObject | null;
    stripeCheckout: AnyObject | null;
    stripeWebhook: AnyObject | null;
    stripeEvents: AnyObject | null;
    auditLog: AnyObject | null;
    cacheSet: AnyObject | null;
    cacheGet: AnyObject | null;
    twilioSms: AnyObject | null;
    twilioCall: AnyObject | null;
    slackMessage: AnyObject | null;
    slackWebhook: AnyObject | null;
    resend: AnyObject | null;
    algoliaIndex: AnyObject | null;
    algoliaQuery: AnyObject | null;
    aiGateway: AnyObject | null;
    totpSetup: AnyObject | null;
    totpVerify: AnyObject | null;
    jwtIssue: AnyObject | null;
    jwtVerify: AnyObject | null;
    tenantCreate: AnyObject | null;
    tenantList: AnyObject | null;
    tenantUpdate: AnyObject | null;
    tenantDelete: AnyObject | null;
    crmContact: AnyObject | null;
    crmDeals: AnyObject | null;
    crmPipeline: AnyObject | null;
    influencerSearch: AnyObject | null;
    influencerCampaign: AnyObject | null;
    chatbot: AnyObject | null;
    linkinbio: AnyObject | null;
    billingPlans: AnyObject | null;
    billingSubscribe: AnyObject | null;
    cmsConnection: AnyObject | null;
    marketplacePlugins: AnyObject | null;
    analyticsDashboard: AnyObject | null;
    notifPrefs: AnyObject | null;
  };

  // ── Control Methods ──────────────────────────────────────
  setApiKey: (key: string) => void;
  setTenantId: (id: string) => void;
  setPublishAt: (time: string) => void;
  setGlobalError: (error: string) => void;
  setContentError: (error: string) => void;
  setIsGeneratingContent: (generating: boolean) => void;
  setLatestTotpSecret: (secret: string) => void;
  setLatestJwtToken: (token: string) => void;

  // ── Output Setters (keyed by endpoint) ───────────────────
  setOutput: <K extends keyof StudioState['outputs']>(key: K, value: AnyObject | null) => void;

  // ── Batch Operations ────────────────────────────────────
  setMultipleOutputs: (updates: Partial<StudioState['outputs']>) => void;
  reset: () => void;
}

const initialOutputs: StudioState['outputs'] = {
  content: null,
  ads: null,
  seo: null,
  social: null,
  listening: null,
  listeningAlerts: null,
  listeningClusters: null,
  reviews: null,
  suitecrm: null,
  refferq: null,
  posthog: null,
  matomo: null,
  plausible: null,
  n8n: null,
  growthbook: null,
  ops: null,
  metrics: null,
  searchIndex: null,
  searchQuery: null,
  webhook: null,
  webhookEvents: null,
  appwriteUser: null,
  appwriteSession: null,
  drone: null,
  directusCreate: null,
  directusList: null,
  minioPresign: null,
  minioList: null,
  stripeCheckout: null,
  stripeWebhook: null,
  stripeEvents: null,
  auditLog: null,
  cacheSet: null,
  cacheGet: null,
  twilioSms: null,
  twilioCall: null,
  slackMessage: null,
  slackWebhook: null,
  resend: null,
  algoliaIndex: null,
  algoliaQuery: null,
  aiGateway: null,
  totpSetup: null,
  totpVerify: null,
  jwtIssue: null,
  jwtVerify: null,
  tenantCreate: null,
  tenantList: null,
  tenantUpdate: null,
  tenantDelete: null,
  crmContact: null,
  crmDeals: null,
  crmPipeline: null,
  influencerSearch: null,
  influencerCampaign: null,
  chatbot: null,
  linkinbio: null,
  billingPlans: null,
  billingSubscribe: null,
  cmsConnection: null,
  marketplacePlugins: null,
  analyticsDashboard: null,
  notifPrefs: null,
};

export const useStudioStore = create<StudioState>((set: any) => ({
  // Initial state
  apiKey: '',
  tenantId: DEFAULT_STUDIO_TENANT_ID,
  publishAt: '',
  globalError: '',
  contentError: '',
  isGeneratingContent: false,
  latestTotpSecret: '',
  latestJwtToken: '',
  outputs: initialOutputs,

  // Control setters
  setApiKey: (key: string) => set({ apiKey: key }),
  setTenantId: (id: string) => set({ tenantId: id }),
  setPublishAt: (time: string) => set({ publishAt: time }),
  setGlobalError: (error: string) => set({ globalError: error }),
  setContentError: (error: string) => set({ contentError: error }),
  setIsGeneratingContent: (generating: boolean) => set({ isGeneratingContent: generating }),
  setLatestTotpSecret: (secret: string) => set({ latestTotpSecret: secret }),
  setLatestJwtToken: (token: string) => set({ latestJwtToken: token }),

  // Output setter
  setOutput: (key: any, value: AnyObject | null) =>
    set((state: any) => ({
      outputs: {
        ...state.outputs,
        [key]: value,
      },
    })),

  // Batch setter for multi-output operations
  setMultipleOutputs: (updates: any) =>
    set((state: any) => ({
      outputs: {
        ...state.outputs,
        ...updates,
      },
    })),

  // Reset all state
  reset: () =>
    set({
      apiKey: '',
      tenantId: DEFAULT_STUDIO_TENANT_ID,
      publishAt: '',
      globalError: '',
      contentError: '',
      isGeneratingContent: false,
      latestTotpSecret: '',
      latestJwtToken: '',
      outputs: initialOutputs,
    }),
}));
