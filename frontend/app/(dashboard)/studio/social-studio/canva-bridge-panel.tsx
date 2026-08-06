'use client';

import Link from 'next/link';
import type { CSSProperties, Dispatch, SetStateAction } from 'react';

export type CanvaPublishMode = 'auto' | 'now' | 'draft';

export type CanvaImportJob = {
  id: number;
  account_id: number;
  design_id?: string;
  design_url?: string;
  resolved_media_url: string;
  post_id: number;
  status: string;
  created_at: string;
};

export type SocialAccount = {
  id: number;
  account_name: string;
  network: string;
};

type CanvaBridgePanelProps = {
  socialAccounts: SocialAccount[];
  canvaAccountId: string;
  setCanvaAccountId: Dispatch<SetStateAction<string>>;
  canvaDesignId: string;
  setCanvaDesignId: Dispatch<SetStateAction<string>>;
  canvaDesignUrl: string;
  setCanvaDesignUrl: Dispatch<SetStateAction<string>>;
  canvaHeadline: string;
  setCanvaHeadline: Dispatch<SetStateAction<string>>;
  canvaCaption: string;
  setCanvaCaption: Dispatch<SetStateAction<string>>;
  canvaPublishMode: CanvaPublishMode;
  setCanvaPublishMode: Dispatch<SetStateAction<CanvaPublishMode>>;
  canvaPublishAt: string;
  setCanvaPublishAt: Dispatch<SetStateAction<string>>;
  canvaImportBusy: boolean;
  canvaImportMessage: string;
  canvaImports: CanvaImportJob[];
  inputStyle: CSSProperties;
  activeBrandKitName?: string;
  activeBrandKitColorsCount?: number;
  activeBrandKitFontsCount?: number;
  onSubmitImport: () => void;
  onApplyActiveBrandKit: () => void;
  onRefreshImports: () => void;
};

export function CanvaBridgePanel({
  socialAccounts,
  canvaAccountId,
  setCanvaAccountId,
  canvaDesignId,
  setCanvaDesignId,
  canvaDesignUrl,
  setCanvaDesignUrl,
  canvaHeadline,
  setCanvaHeadline,
  canvaCaption,
  setCanvaCaption,
  canvaPublishMode,
  setCanvaPublishMode,
  canvaPublishAt,
  setCanvaPublishAt,
  canvaImportBusy,
  canvaImportMessage,
  canvaImports,
  inputStyle,
  activeBrandKitName,
  activeBrandKitColorsCount,
  activeBrandKitFontsCount,
  onSubmitImport,
  onApplyActiveBrandKit,
  onRefreshImports,
}: Readonly<CanvaBridgePanelProps>) {
  const selectedAccount = socialAccounts.find((account) => String(account.id) === canvaAccountId) ?? null;

  return (
    <div className="ops-panel-grid" style={{ marginTop: 20 }}>
      <section className="ops-panel">
        <div className="section-header-row">
          <h4>Canva bridge</h4>
          <span className="suggestion-chip">Import to schedule</span>
        </div>
        <p className="small-text">
          Use an existing Canva design URL or design ID, then schedule it against a connected social account.
        </p>
        {activeBrandKitName ? (
          <div className="result-card" style={{ marginBottom: 10 }}>
            <p>
              <strong>Brand kit:</strong> {activeBrandKitName}
            </p>
            <p style={{ fontSize: 11, marginTop: 4 }}>
              Colors: {activeBrandKitColorsCount ?? 0} · Fonts: {activeBrandKitFontsCount ?? 0}
            </p>
          </div>
        ) : null}
        <div className="dual-grid compact">
          <div className="field">
            <label htmlFor="canva-account">Connected account</label>
            <select
              id="canva-account"
              value={canvaAccountId}
              onChange={(event) => setCanvaAccountId(event.target.value)}
              style={inputStyle}
            >
              {socialAccounts.length === 0 ? (
                <option value="">Connect a social account first</option>
              ) : (
                socialAccounts.map((account) => (
                  <option key={account.id} value={String(account.id)}>
                    {account.account_name} ({account.network})
                  </option>
                ))
              )}
            </select>
          </div>
          <div className="field">
            <label htmlFor="canva-target-network">Target network</label>
            <input
              id="canva-target-network"
              value={selectedAccount?.network || ''}
              readOnly
              style={{ ...inputStyle, opacity: 0.85 }}
            />
          </div>
        </div>
        <div className="field">
          <label htmlFor="canva-design-id">Design ID</label>
          <input
            id="canva-design-id"
            value={canvaDesignId}
            onChange={(event) => setCanvaDesignId(event.target.value)}
            style={inputStyle}
            placeholder="design_123456"
          />
        </div>
        <div className="field">
          <label htmlFor="canva-design-url">Design URL</label>
          <input
            id="canva-design-url"
            value={canvaDesignUrl}
            onChange={(event) => setCanvaDesignUrl(event.target.value)}
            style={inputStyle}
            placeholder="https://www.canva.com/design/..."
          />
        </div>
        <div className="dual-grid compact">
          <div className="field">
            <label htmlFor="canva-headline">Headline</label>
            <input
              id="canva-headline"
              value={canvaHeadline}
              onChange={(event) => setCanvaHeadline(event.target.value)}
              style={inputStyle}
            />
          </div>
          <div className="field">
            <label htmlFor="canva-caption">Caption</label>
            <input
              id="canva-caption"
              value={canvaCaption}
              onChange={(event) => setCanvaCaption(event.target.value)}
              style={inputStyle}
            />
          </div>
        </div>
        <div className="dual-grid compact">
          <div className="field">
            <label htmlFor="canva-publish-mode">Publish mode</label>
            <select
              id="canva-publish-mode"
              value={canvaPublishMode}
              onChange={(event) => setCanvaPublishMode(event.target.value as CanvaPublishMode)}
              style={inputStyle}
            >
              <option value="draft">draft</option>
              <option value="now">now</option>
              <option value="auto">auto</option>
            </select>
          </div>
          <div className="field">
            <label htmlFor="canva-publish-at">Publish at</label>
            <input
              id="canva-publish-at"
              type="datetime-local"
              value={canvaPublishAt}
              onChange={(event) => setCanvaPublishAt(event.target.value)}
              style={inputStyle}
              disabled={canvaPublishMode === 'draft'}
            />
          </div>
        </div>
        <div className="command-grid compact-grid">
          <button
            type="button"
            className="command-btn command-btn-primary"
            disabled={canvaImportBusy}
            onClick={onSubmitImport}
          >
            {canvaImportBusy ? 'Importing…' : 'Import Canva design'}
          </button>
          <button type="button" className="command-btn command-btn-muted" onClick={onApplyActiveBrandKit}>
            Use active brand kit
          </button>
          <Link
            href="/studio/editor"
            className="command-btn command-btn-muted"
            style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', textDecoration: 'none' }}
          >
            Open canvas editor
          </Link>
          <button type="button" className="command-btn command-btn-muted" onClick={onRefreshImports}>
            Refresh imports
          </button>
        </div>
        {canvaImportMessage ? (
          <p className="small-text" style={{ marginTop: 10 }}>
            {canvaImportMessage}
          </p>
        ) : null}
      </section>

      <section className="ops-panel">
        <h4>Recent Canva imports</h4>
        {canvaImports.length === 0 ? (
          <p className="small-text">No Canva imports yet.</p>
        ) : (
          <div className="ops-list">
            {canvaImports.slice(0, 6).map((job) => (
              <article key={job.id} className="ops-list-item">
                <div className="ops-account-info">
                  <strong>{job.design_id || job.design_url || `Import ${job.id}`}</strong>
                  <span>
                    {job.status} · post {job.post_id}
                  </span>
                </div>
                <span className="ops-account-status-label">{new Date(job.created_at).toLocaleString()}</span>
              </article>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
