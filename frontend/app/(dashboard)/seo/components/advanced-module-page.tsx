'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';

import { apiGet, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';
import { Badge, Card, CardTitle, Page, PageHeader, Stat, StatGrid } from '../../_ui/kit';
import { getCatalogByModuleKey } from '../module-catalog';

type SeoModule = {
  key: string;
  group: string;
  display_name: string;
  description: string;
  route_path: string;
  badge?: string | null;
  implemented: boolean;
  backend_ready: boolean;
  frontend_ready: boolean;
  database_ready: boolean;
  integrations: string[];
  supported_channels?: string[];
  architecture_layers?: string[];
  automation_features?: string[];
  analytics_features?: string[];
  enterprise_features?: string[];
  ai_models?: string[];
  delivery_constraints?: string[];
};

type ModuleDetailResponse = {
  module: SeoModule;
};

type HeroMetric = {
  label: string;
  value: string;
  hint: string;
};

type AdvancedModulePageProps = {
  moduleKey: string;
  eyebrow: string;
  title: string;
  summary: string;
  heroMetrics: HeroMetric[];
  executionLanes: string[];
  operatingModel: string[];
};

function ChecklistCard({ title, items }: Readonly<{ title: string; items?: string[] }>) {
  if (!items || items.length === 0) return null;
  return (
    <Card>
      <CardTitle>{title}</CardTitle>
      <div style={{ display: 'grid', gap: 10, marginTop: 14 }}>
        {items.map((item) => (
          <div key={`${title}-${item}`} style={{ fontSize: 13, lineHeight: 1.55, color: 'var(--nx-ink)' }}>
            {item}
          </div>
        ))}
      </div>
    </Card>
  );
}

export default function AdvancedModulePage(props: Readonly<AdvancedModulePageProps>) {
  const [moduleDetail, setModuleDetail] = useState<SeoModule | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    async function loadModule() {
      try {
        const response = await apiGet<ModuleDetailResponse>(
          `/seo-platform/modules/${props.moduleKey}`,
          DEFAULT_TENANT_ID
        );
        if (active) {
          setModuleDetail(response.module);
          setError('');
        }
      } catch (err) {
        if (active) setError(err instanceof Error ? err.message : 'Module unavailable.');
      }
    }

    void loadModule();
    return () => {
      active = false;
    };
  }, [props.moduleKey]);

  const catalog = getCatalogByModuleKey(props.moduleKey);
  const pending = [
    !moduleDetail?.frontend_ready && 'Frontend',
    !moduleDetail?.backend_ready && 'Backend',
    !moduleDetail?.database_ready && 'Database',
    !moduleDetail?.implemented && 'Implementation',
  ].filter(Boolean) as string[];

  return (
    <Page>
      <PageHeader
        title={catalog?.title ?? props.title}
        subtitle={catalog?.summary ?? props.summary}
        actions={
          <Link href="/seo" style={{ color: 'var(--nx-brand)', textDecoration: 'none', fontSize: 13, fontWeight: 600 }}>
            Back to SEO
          </Link>
        }
      />

      {pending.length > 0 ? (
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {pending.map((item) => (
            <Badge key={item} tone="danger">
              {item} pending
            </Badge>
          ))}
        </div>
      ) : moduleDetail ? (
        <Badge tone="success">Ready</Badge>
      ) : null}

      {error && (
        <Card>
          <p style={{ margin: 0, color: '#b91c1c' }}>{error}</p>
        </Card>
      )}

      <StatGrid>
        {props.heroMetrics.map((metric) => (
          <Stat key={metric.label} label={metric.label} value={metric.value} hint={metric.hint} />
        ))}
      </StatGrid>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 280px), 1fr))', gap: 14 }}>
        <Card>
          <CardTitle>What this module does</CardTitle>
          <div style={{ display: 'grid', gap: 10, marginTop: 14 }}>
            {props.executionLanes.map((lane) => (
              <div key={lane} style={{ fontSize: 13, lineHeight: 1.55 }}>
                {lane}
              </div>
            ))}
          </div>
        </Card>
        <Card>
          <CardTitle>How it runs</CardTitle>
          <div style={{ display: 'grid', gap: 12, marginTop: 14 }}>
            {props.operatingModel.map((item) => (
              <div key={item} style={{ fontSize: 13, lineHeight: 1.55 }}>
                {item}
              </div>
            ))}
          </div>
        </Card>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 260px), 1fr))', gap: 14 }}>
        <ChecklistCard title="Channels" items={moduleDetail?.supported_channels} />
        <ChecklistCard title="Integrations" items={moduleDetail?.integrations} />
        <ChecklistCard title="Models" items={moduleDetail?.ai_models} />
        <ChecklistCard title="Architecture" items={moduleDetail?.architecture_layers} />
        <ChecklistCard title="Automation" items={moduleDetail?.automation_features} />
        <ChecklistCard title="Analytics" items={moduleDetail?.analytics_features} />
        <ChecklistCard title="Enterprise controls" items={moduleDetail?.enterprise_features} />
        <ChecklistCard title="Constraints" items={moduleDetail?.delivery_constraints} />
      </div>
    </Page>
  );
}
