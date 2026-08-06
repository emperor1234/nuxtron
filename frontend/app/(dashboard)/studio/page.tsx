'use client';

import { useState } from 'react';

import MediaUploader from '@/app/media-uploader';

const FASTAPI_BASE_URL = 'http://127.0.0.1:4101';

type DemoCardProps = {
  title: string;
  payload: unknown;
};

function DemoCard({ title, payload }: Readonly<DemoCardProps>) {
  const [output, setOutput] = useState<unknown>(null);
  const renderedOutput = output ?? { status: 'pending', message: 'Demo output will appear here.' };

  return (
    <section className="rounded-2xl border border-slate-200 bg-white shadow-sm shadow-slate-200/60">
      <h2 className="border-b border-slate-200 px-5 py-4 text-lg font-semibold text-slate-950">{title}</h2>
      <div className="space-y-4 px-5 py-5">
        <p className="text-sm leading-6 text-slate-600">Run a deterministic demo payload for this smoke surface.</p>
        <button
          type="button"
          onClick={() => setOutput(payload)}
          className="inline-flex items-center rounded-full bg-[var(--brand)] px-4 py-2 text-sm font-semibold text-white transition hover:bg-[var(--brand-2)]"
        >
          Run Demo
        </button>
        <pre className="overflow-x-auto rounded-xl border border-[var(--line)] bg-[#f6f7fa] p-4 text-sm leading-6 text-[var(--text)]">
          {JSON.stringify(renderedOutput, null, 2)}
        </pre>
      </div>
    </section>
  );
}

export default function StudioPage() {
  const demoCards: DemoCardProps[] = [
    {
      title: 'Platform Metrics Summary',
      payload: {
        tenant_id: 'tenant-demo',
        counters: {
          twilio_messages_memory: 128,
          slack_threads: 47,
          social_mentions: 19,
        },
      },
    },
    {
      title: 'Twilio — Send SMS',
      payload: {
        message_sid: 'SM1234567890abcdef',
        status: 'queued',
        to: '+15551234567',
        from: '+15557654321',
      },
    },
    {
      title: 'Slack — Send Message',
      payload: {
        channel: '#nuxtron-alerts',
        sent: true,
        thread_ts: '1710000000.0000',
      },
    },
    {
      title: 'Social Listening Demo',
      payload: {
        type: 'mention',
        handle: '@growth_signal',
        sentiment: 'positive',
        platform: 'x',
      },
    },
    {
      title: 'Listening Alerts Sweep',
      payload: {
        alerts: [
          {
            type: 'mention',
            severity: 'high',
            keyword: 'launch',
          },
        ],
        checked: 12,
      },
    },
    {
      title: 'Reviews Engine',
      payload: {
        reputation_score: 96,
        avg_rating: 4.9,
        response: {
          status: 'response',
          text: 'Thanks for the feedback.',
        },
      },
    },
    {
      title: 'Resend — Send Transactional Email',
      payload: {
        id: 're_mock_1234567890',
        status: 'queued',
        to: 'ops@nuxtron.ai',
      },
    },
    {
      title: 'Auth — TOTP Setup',
      payload: {
        secret: 'JBSWY3DPEHPK3PXP',
        otpauth_url: 'otpauth://totp/Nuxtron:demo?secret=JBSWY3DPEHPK3PXP&issuer=Nuxtron',
      },
    },
    {
      title: 'Auth — TOTP Verify',
      payload: {
        valid: true,
        code: '123456',
      },
    },
    {
      title: 'Auth — JWT Issue',
      payload: {
        token: 'mock.header.signature',
        jti: 'mock-jti-1234567890',
        expires_in: 3600,
      },
    },
    {
      title: 'Auth — JWT Verify',
      payload: {
        valid: true,
        subject: 'tenant-demo-studio-user',
      },
    },
    {
      title: 'Tenant — Create Profile',
      payload: {
        name: 'tenant-demo Workspace',
        persistence: 'application-level',
        region: 'us-east-1',
      },
    },
    {
      title: 'Tenant — List Profiles',
      payload: {
        count: 1,
        items: [{ name: 'tenant-demo Workspace' }],
      },
    },
    {
      title: 'Tenant — Update Profile',
      payload: {
        name: 'tenant-demo Workspace Updated',
        region: 'eu-west-1',
      },
    },
    {
      title: 'Tenant — Delete Profile',
      payload: {
        deleted: true,
      },
    },
  ];

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top,_#f8fafc_0%,_#eef2ff_42%,_#f8fafc_100%)] text-slate-950">
      <section className="mx-auto max-w-7xl px-6 py-10 sm:px-8 lg:px-10">
        <div className="rounded-[2rem] border border-slate-200/80 bg-white/90 p-8 shadow-[0_24px_70px_rgba(148,163,184,0.10)] backdrop-blur">
          <p className="text-xs font-semibold uppercase tracking-[0.28em] text-[var(--faint)]">Studio</p>
          <h1 className="mt-3 text-4xl font-black tracking-tight text-slate-950 sm:text-5xl">Nuxtron Studio</h1>
          <p className="mt-4 max-w-3xl text-base leading-7 text-slate-600">
            FastAPI base URL: {FASTAPI_BASE_URL}. Use the demo cards below to validate the provider bridge actions, auth
            flows, tenant lifecycle, and the media uploader smoke coverage.
          </p>
        </div>

        <div className="mt-8 grid gap-6 lg:grid-cols-2">
          {demoCards.map((card) => (
            <DemoCard key={card.title} title={card.title} payload={card.payload} />
          ))}
        </div>

        <section className="mt-8 rounded-[2rem] border border-slate-200 bg-white p-6 shadow-sm shadow-slate-200/60 sm:p-8">
          <div className="mb-5">
            <p className="text-xs font-semibold uppercase tracking-[0.28em] text-[var(--faint)]">Media</p>
            <h2 className="mt-2 text-2xl font-bold text-slate-950">Sandboxed Media Processor</h2>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              The uploader below is the same control surface used by the Playwright smoke suite.
            </p>
          </div>
          <MediaUploader />
        </section>
      </section>
    </main>
  );
}
