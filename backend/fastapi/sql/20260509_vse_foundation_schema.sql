-- NUXTRON VSE foundation schema (additive + idempotent)
-- Adds missing relational structures for the Viral Singularity Engine.
-- This migration is intentionally additive and does not alter existing core schema objects.

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'campaign_status') THEN
    CREATE TYPE campaign_status AS ENUM ('draft','active','paused','completed','archived');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'content_type') THEN
    CREATE TYPE content_type AS ENUM ('post','video','story','reel','thread','audio','image','poll','quiz');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'share_platform') THEN
    CREATE TYPE share_platform AS ENUM ('twitter','instagram','tiktok','facebook','linkedin','whatsapp','telegram','reddit','email','sms','copy_link','qr_code','embed','native_share');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'hook_type') THEN
    CREATE TYPE hook_type AS ENUM ('fomo','social_proof','curiosity','authority','reciprocity','scarcity','belonging','achievement');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'virality_tier') THEN
    CREATE TYPE virality_tier AS ENUM ('dormant','spark','flame','wildfire','singularity');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'ab_variant') THEN
    CREATE TYPE ab_variant AS ENUM ('control','variant_a','variant_b','variant_c');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'referral_status') THEN
    CREATE TYPE referral_status AS ENUM ('pending','accepted','converted','expired','fraudulent');
  END IF;
END
$$;

CREATE TABLE IF NOT EXISTS public.profiles (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  username TEXT UNIQUE NOT NULL,
  display_name TEXT NOT NULL,
  avatar_url TEXT,
  bio_encrypted BYTEA,
  email_encrypted BYTEA,
  phone_encrypted BYTEA,
  timezone TEXT DEFAULT 'UTC',
  locale TEXT DEFAULT 'en',
  referral_code TEXT UNIQUE NOT NULL DEFAULT encode(gen_random_bytes(6), 'hex'),
  referred_by UUID REFERENCES public.profiles(id),
  singularity_score NUMERIC(6,2) DEFAULT 0,
  k_factor NUMERIC(8,4) DEFAULT 0,
  total_referrals INTEGER DEFAULT 0,
  total_conversions INTEGER DEFAULT 0,
  total_shares BIGINT DEFAULT 0,
  network_size INTEGER DEFAULT 0,
  influence_rank NUMERIC(8,4) DEFAULT 0,
  is_influencer BOOLEAN DEFAULT false,
  onboarding_done BOOLEAN DEFAULT false,
  metadata JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.organizations (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name TEXT NOT NULL,
  slug TEXT UNIQUE NOT NULL,
  plan TEXT NOT NULL DEFAULT 'starter',
  owner_id UUID NOT NULL REFERENCES public.profiles(id),
  logo_url TEXT,
  settings JSONB DEFAULT '{}'::jsonb,
  api_key_hash TEXT,
  viral_budget NUMERIC(12,2) DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.organization_members (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  org_id UUID NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
  role TEXT NOT NULL DEFAULT 'member' CHECK (role IN ('owner','admin','member','viewer')),
  permissions JSONB DEFAULT '{}'::jsonb,
  invited_by UUID REFERENCES public.profiles(id),
  joined_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (org_id, user_id)
);

CREATE TABLE IF NOT EXISTS public.campaigns (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  org_id UUID NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
  created_by UUID NOT NULL REFERENCES public.profiles(id),
  name TEXT NOT NULL,
  slug TEXT NOT NULL,
  description TEXT,
  status campaign_status DEFAULT 'draft',
  goal TEXT,
  target_k_factor NUMERIC(8,4) DEFAULT 1.5,
  target_virality virality_tier DEFAULT 'flame',
  budget NUMERIC(12,2) DEFAULT 0,
  spent NUMERIC(12,2) DEFAULT 0,
  start_date TIMESTAMPTZ,
  end_date TIMESTAMPTZ,
  current_k_factor NUMERIC(8,4) DEFAULT 0,
  singularity_score NUMERIC(6,2) DEFAULT 0,
  total_reach BIGINT DEFAULT 0,
  total_shares BIGINT DEFAULT 0,
  total_conversions INTEGER DEFAULT 0,
  conversion_rate NUMERIC(6,4) DEFAULT 0,
  velocity_score NUMERIC(8,4) DEFAULT 0,
  tipping_point_eta TIMESTAMPTZ,
  reward_config JSONB DEFAULT '{}'::jsonb,
  hook_config JSONB DEFAULT '{}'::jsonb,
  loop_config JSONB DEFAULT '{}'::jsonb,
  ab_config JSONB DEFAULT '{}'::jsonb,
  targeting_config JSONB DEFAULT '{}'::jsonb,
  metadata JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (org_id, slug)
);

CREATE TABLE IF NOT EXISTS public.content_pieces (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  campaign_id UUID REFERENCES public.campaigns(id) ON DELETE CASCADE,
  org_id UUID NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
  created_by UUID NOT NULL REFERENCES public.profiles(id),
  title TEXT NOT NULL,
  body TEXT,
  content_type content_type NOT NULL,
  media_urls TEXT[] DEFAULT '{}'::text[],
  thumbnail_url TEXT,
  virality_score NUMERIC(6,2) DEFAULT 0,
  hook_strength NUMERIC(6,2) DEFAULT 0,
  share_dna JSONB DEFAULT '{}'::jsonb,
  emotion_tags TEXT[] DEFAULT '{}'::text[],
  view_count BIGINT DEFAULT 0,
  share_count BIGINT DEFAULT 0,
  engagement_rate NUMERIC(6,4) DEFAULT 0,
  avg_watch_time NUMERIC(8,2),
  ab_variant ab_variant DEFAULT 'control',
  ab_experiment_id UUID,
  is_published BOOLEAN DEFAULT false,
  published_at TIMESTAMPTZ,
  metadata JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.viral_loops (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  campaign_id UUID NOT NULL REFERENCES public.campaigns(id) ON DELETE CASCADE,
  org_id UUID NOT NULL REFERENCES public.organizations(id),
  name TEXT NOT NULL,
  description TEXT,
  loop_config JSONB NOT NULL DEFAULT '{}'::jsonb,
  hook_types hook_type[] DEFAULT '{}'::hook_type[],
  is_active BOOLEAN DEFAULT true,
  loop_count BIGINT DEFAULT 0,
  avg_loop_time NUMERIC(10,2),
  completion_rate NUMERIC(6,4) DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.referrals (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  campaign_id UUID REFERENCES public.campaigns(id),
  org_id UUID NOT NULL REFERENCES public.organizations(id),
  referrer_id UUID NOT NULL REFERENCES public.profiles(id),
  referee_id UUID REFERENCES public.profiles(id),
  referral_code TEXT NOT NULL,
  status referral_status DEFAULT 'pending',
  tier INTEGER DEFAULT 1,
  reward_id UUID,
  platform share_platform,
  ip_hash TEXT,
  user_agent_hash TEXT,
  utm_source TEXT,
  utm_medium TEXT,
  utm_campaign TEXT,
  click_at TIMESTAMPTZ,
  converted_at TIMESTAMPTZ,
  revenue_attributed NUMERIC(12,2) DEFAULT 0,
  metadata JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.share_events (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  campaign_id UUID REFERENCES public.campaigns(id),
  content_id UUID REFERENCES public.content_pieces(id),
  org_id UUID NOT NULL REFERENCES public.organizations(id),
  user_id UUID REFERENCES public.profiles(id),
  platform share_platform NOT NULL,
  referral_code TEXT,
  deep_link TEXT,
  clicks INTEGER DEFAULT 0,
  conversions INTEGER DEFAULT 0,
  reach INTEGER DEFAULT 0,
  ip_hash TEXT,
  device_hash TEXT,
  country_code CHAR(2),
  region TEXT,
  utm_params JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.deep_links (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  campaign_id UUID REFERENCES public.campaigns(id),
  content_id UUID REFERENCES public.content_pieces(id),
  org_id UUID NOT NULL REFERENCES public.organizations(id),
  created_by UUID REFERENCES public.profiles(id),
  short_code TEXT UNIQUE NOT NULL DEFAULT encode(gen_random_bytes(4), 'hex'),
  destination_url TEXT NOT NULL,
  platform share_platform,
  og_title TEXT,
  og_description TEXT,
  og_image TEXT,
  custom_domain TEXT,
  click_count BIGINT DEFAULT 0,
  unique_clicks BIGINT DEFAULT 0,
  conversion_count INTEGER DEFAULT 0,
  is_active BOOLEAN DEFAULT true,
  expires_at TIMESTAMPTZ,
  metadata JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.hooks (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  campaign_id UUID REFERENCES public.campaigns(id),
  org_id UUID NOT NULL REFERENCES public.organizations(id),
  name TEXT NOT NULL,
  hook_type hook_type NOT NULL,
  trigger_config JSONB NOT NULL DEFAULT '{}'::jsonb,
  display_config JSONB NOT NULL DEFAULT '{}'::jsonb,
  audience_config JSONB DEFAULT '{}'::jsonb,
  is_active BOOLEAN DEFAULT true,
  impressions BIGINT DEFAULT 0,
  clicks BIGINT DEFAULT 0,
  conversions INTEGER DEFAULT 0,
  ctr NUMERIC(6,4) DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.ab_experiments (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  campaign_id UUID REFERENCES public.campaigns(id),
  org_id UUID NOT NULL REFERENCES public.organizations(id),
  name TEXT NOT NULL,
  hypothesis TEXT,
  metric TEXT NOT NULL DEFAULT 'k_factor',
  variants JSONB NOT NULL DEFAULT '[]'::jsonb,
  status TEXT DEFAULT 'draft' CHECK (status IN ('draft','running','paused','completed')),
  winner_variant ab_variant,
  confidence NUMERIC(6,4),
  started_at TIMESTAMPTZ,
  ended_at TIMESTAMPTZ,
  results JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.rewards (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  campaign_id UUID REFERENCES public.campaigns(id),
  org_id UUID NOT NULL REFERENCES public.organizations(id),
  name TEXT NOT NULL,
  kind TEXT NOT NULL,
  value_text TEXT,
  inventory_count INTEGER,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.reward_claims (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  reward_id UUID NOT NULL REFERENCES public.rewards(id) ON DELETE CASCADE,
  campaign_id UUID REFERENCES public.campaigns(id),
  user_id UUID NOT NULL REFERENCES public.profiles(id),
  org_id UUID NOT NULL REFERENCES public.organizations(id),
  claimed_at TIMESTAMPTZ DEFAULT NOW(),
  status TEXT NOT NULL DEFAULT 'claimed',
  metadata JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS public.viral_metrics (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  org_id UUID NOT NULL REFERENCES public.organizations(id),
  campaign_id UUID REFERENCES public.campaigns(id),
  metric_date DATE NOT NULL,
  metric_hour SMALLINT,
  k_factor NUMERIC(8,4) DEFAULT 0,
  singularity_score NUMERIC(6,2) DEFAULT 0,
  total_shares BIGINT DEFAULT 0,
  total_conversions INTEGER DEFAULT 0,
  conversion_rate NUMERIC(6,4) DEFAULT 0,
  velocity_score NUMERIC(8,4) DEFAULT 0,
  metadata JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (org_id, campaign_id, metric_date, metric_hour)
);

CREATE TABLE IF NOT EXISTS public.network_edges (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  org_id UUID NOT NULL REFERENCES public.organizations(id),
  campaign_id UUID REFERENCES public.campaigns(id),
  source_id UUID NOT NULL REFERENCES public.profiles(id),
  target_id UUID NOT NULL REFERENCES public.profiles(id),
  weight NUMERIC(8,4) DEFAULT 1,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (org_id, source_id, target_id, campaign_id)
);

CREATE TABLE IF NOT EXISTS public.influencers (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  org_id UUID NOT NULL REFERENCES public.organizations(id),
  profile_id UUID REFERENCES public.profiles(id),
  handle TEXT,
  platform share_platform,
  followers BIGINT DEFAULT 0,
  engagement_rate NUMERIC(6,4) DEFAULT 0,
  status TEXT DEFAULT 'active',
  metadata JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.webhooks (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  org_id UUID NOT NULL REFERENCES public.organizations(id),
  event TEXT NOT NULL,
  endpoint_encrypted BYTEA,
  secret_hash TEXT,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.audit_logs (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  org_id UUID REFERENCES public.organizations(id),
  user_id UUID REFERENCES public.profiles(id),
  action TEXT NOT NULL,
  details JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_profiles_referral_code ON public.profiles(referral_code);
CREATE INDEX IF NOT EXISTS idx_profiles_referred_by ON public.profiles(referred_by);
CREATE INDEX IF NOT EXISTS idx_campaigns_org_id ON public.campaigns(org_id);
CREATE INDEX IF NOT EXISTS idx_campaigns_status ON public.campaigns(status);
CREATE INDEX IF NOT EXISTS idx_content_campaign ON public.content_pieces(campaign_id);
CREATE INDEX IF NOT EXISTS idx_referrals_referrer ON public.referrals(referrer_id);
CREATE INDEX IF NOT EXISTS idx_referrals_campaign ON public.referrals(campaign_id);
CREATE INDEX IF NOT EXISTS idx_referrals_status ON public.referrals(status);
CREATE INDEX IF NOT EXISTS idx_shares_campaign ON public.share_events(campaign_id);
CREATE INDEX IF NOT EXISTS idx_shares_platform ON public.share_events(platform);
CREATE INDEX IF NOT EXISTS idx_deep_links_short_code ON public.deep_links(short_code);
CREATE INDEX IF NOT EXISTS idx_viral_metrics_org_date ON public.viral_metrics(org_id, metric_date DESC);
CREATE INDEX IF NOT EXISTS idx_network_source ON public.network_edges(source_id);
CREATE INDEX IF NOT EXISTS idx_network_target ON public.network_edges(target_id);
CREATE INDEX IF NOT EXISTS idx_audit_org ON public.audit_logs(org_id, created_at DESC);

CREATE OR REPLACE FUNCTION public.update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$
DECLARE t TEXT;
BEGIN
  FOREACH t IN ARRAY ARRAY[
    'profiles','organizations','campaigns','content_pieces','viral_loops',
    'referrals','hooks','ab_experiments','rewards','influencers'
  ]
  LOOP
    EXECUTE format('DROP TRIGGER IF EXISTS trg_updated_at ON public.%I', t);
    EXECUTE format('CREATE TRIGGER trg_updated_at BEFORE UPDATE ON public.%I FOR EACH ROW EXECUTE FUNCTION public.update_updated_at()', t);
  END LOOP;
END
$$;

ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.organization_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.campaigns ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.content_pieces ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.viral_loops ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.referrals ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.share_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.deep_links ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.hooks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ab_experiments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.rewards ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.reward_claims ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.viral_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.influencers ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_logs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS profiles_select ON public.profiles;
CREATE POLICY profiles_select ON public.profiles
  FOR SELECT USING (
    id = auth.uid()
    OR EXISTS (
      SELECT 1 FROM public.organization_members m
      WHERE m.user_id = public.profiles.id
        AND m.org_id IN (
          SELECT org_id FROM public.organization_members WHERE user_id = auth.uid()
        )
    )
  );

DROP POLICY IF EXISTS profiles_update ON public.profiles;
CREATE POLICY profiles_update ON public.profiles
  FOR UPDATE USING (id = auth.uid());

DROP POLICY IF EXISTS orgs_select ON public.organizations;
CREATE POLICY orgs_select ON public.organizations
  FOR SELECT USING (
    id IN (SELECT org_id FROM public.organization_members WHERE user_id = auth.uid())
  );

DROP POLICY IF EXISTS orgs_insert ON public.organizations;
CREATE POLICY orgs_insert ON public.organizations
  FOR INSERT WITH CHECK (owner_id = auth.uid());

DROP POLICY IF EXISTS orgs_update ON public.organizations;
CREATE POLICY orgs_update ON public.organizations
  FOR UPDATE USING (
    owner_id = auth.uid()
    OR id IN (
      SELECT org_id FROM public.organization_members
      WHERE user_id = auth.uid() AND role IN ('owner','admin')
    )
  );

DROP POLICY IF EXISTS campaigns_select ON public.campaigns;
CREATE POLICY campaigns_select ON public.campaigns
  FOR SELECT USING (
    org_id IN (SELECT org_id FROM public.organization_members WHERE user_id = auth.uid())
  );

DROP POLICY IF EXISTS campaigns_insert ON public.campaigns;
CREATE POLICY campaigns_insert ON public.campaigns
  FOR INSERT WITH CHECK (
    org_id IN (
      SELECT org_id FROM public.organization_members
      WHERE user_id = auth.uid() AND role IN ('owner','admin','member')
    )
  );

DROP POLICY IF EXISTS campaigns_update ON public.campaigns;
CREATE POLICY campaigns_update ON public.campaigns
  FOR UPDATE USING (
    org_id IN (
      SELECT org_id FROM public.organization_members
      WHERE user_id = auth.uid() AND role IN ('owner','admin','member')
    )
  );

DROP POLICY IF EXISTS campaigns_delete ON public.campaigns;
CREATE POLICY campaigns_delete ON public.campaigns
  FOR DELETE USING (
    org_id IN (
      SELECT org_id FROM public.organization_members
      WHERE user_id = auth.uid() AND role IN ('owner','admin')
    )
  );

DROP POLICY IF EXISTS referrals_select ON public.referrals;
CREATE POLICY referrals_select ON public.referrals
  FOR SELECT USING (
    referrer_id = auth.uid()
    OR referee_id = auth.uid()
    OR org_id IN (SELECT org_id FROM public.organization_members WHERE user_id = auth.uid())
  );

DROP POLICY IF EXISTS referrals_insert ON public.referrals;
CREATE POLICY referrals_insert ON public.referrals
  FOR INSERT WITH CHECK (true);

DROP POLICY IF EXISTS share_events_select ON public.share_events;
CREATE POLICY share_events_select ON public.share_events
  FOR SELECT USING (
    org_id IN (SELECT org_id FROM public.organization_members WHERE user_id = auth.uid())
  );

DROP POLICY IF EXISTS share_events_insert ON public.share_events;
CREATE POLICY share_events_insert ON public.share_events
  FOR INSERT WITH CHECK (true);

DROP POLICY IF EXISTS viral_metrics_select ON public.viral_metrics;
CREATE POLICY viral_metrics_select ON public.viral_metrics
  FOR SELECT USING (
    org_id IN (SELECT org_id FROM public.organization_members WHERE user_id = auth.uid())
  );

DROP POLICY IF EXISTS reward_claims_select ON public.reward_claims;
CREATE POLICY reward_claims_select ON public.reward_claims
  FOR SELECT USING (
    user_id = auth.uid()
    OR campaign_id IN (
      SELECT id FROM public.campaigns
      WHERE org_id IN (
        SELECT org_id FROM public.organization_members WHERE user_id = auth.uid()
      )
    )
  );

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_publication WHERE pubname = 'supabase_realtime') THEN
    ALTER PUBLICATION supabase_realtime ADD TABLE public.campaigns;
    ALTER PUBLICATION supabase_realtime ADD TABLE public.share_events;
    ALTER PUBLICATION supabase_realtime ADD TABLE public.referrals;
    ALTER PUBLICATION supabase_realtime ADD TABLE public.viral_metrics;
  END IF;
EXCEPTION
  WHEN duplicate_object THEN
    NULL;
END
$$;
