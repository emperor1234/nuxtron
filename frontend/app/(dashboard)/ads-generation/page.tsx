'use client';

import { useState, type FormEvent } from 'react';
import { resolveSessionTenant } from '@/app/lib/api-client';
import { apiSend } from '@/app/lib/platform-api';
import { Badge, Button, Card, CardTitle, Field, FieldSelect, Page, PageHeader } from '../_ui/kit';
import { parseAdsGenerationResult, type AdsGenerationResult } from './ads-generation-model';
import styles from './ads-generation.module.css';

function sessionWorkspace(): string {
  try {
    return resolveSessionTenant();
  } catch {
    return '';
  }
}

export default function AdsGenerationPage() {
  const [tenantId] = useState(sessionWorkspace);
  const [product, setProduct] = useState('');
  const [audience, setAudience] = useState('');
  const [platform, setPlatform] = useState('');
  const [objective, setObjective] = useState('');
  const [result, setResult] = useState<AdsGenerationResult | null>(null);
  const [error, setError] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [copyStatus, setCopyStatus] = useState('');

  const hasWorkspace = tenantId.trim().length > 0;
  const canGenerate = hasWorkspace && product.trim().length >= 2 && audience.trim().length >= 2 && !!platform && !!objective;

  async function run(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const cleanProduct = product.trim();
    const cleanAudience = audience.trim();
    if (!hasWorkspace) {
      setError('Sign in and select a workspace before generating ad copy.');
      return;
    }
    if (cleanProduct.length < 2 || cleanAudience.length < 2 || !platform || !objective) {
      setError('Complete the product, audience, advertising platform, and campaign objective before generating.');
      return;
    }

    setError('');
    setCopyStatus('');
    setResult(null);
    setIsGenerating(true);
    try {
      const response = await apiSend<unknown>(
        '/ads/generate',
        'POST',
        { product: cleanProduct, audience: cleanAudience, platform, objective },
        tenantId
      );
      const parsed = parseAdsGenerationResult(response);
      if (!parsed) throw new Error('The ad-generation service returned an incomplete response. Please retry.');
      setResult(parsed);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Ad copy could not be generated. Please retry.');
    } finally {
      setIsGenerating(false);
    }
  }

  async function copyGeneratedText() {
    if (!result || result.ai_status !== 'generated') return;
    try {
      if (!navigator.clipboard?.writeText) throw new Error('Clipboard access is unavailable.');
      await navigator.clipboard.writeText(result.outputs.text);
      setCopyStatus('Ad copy copied to clipboard.');
    } catch {
      setCopyStatus('Copy is unavailable here. Select the ad copy below and copy it manually.');
    }
  }

  return (
    <Page className={styles.layout}>
      <PageHeader
        title="AI ad generation"
        subtitle="Create channel-specific ad copy from a brief you provide. Nothing is generated until you submit it."
        actions={<Badge tone="neutral">Workspace scoped</Badge>}
      />

      {!hasWorkspace ? (
        <p role="alert" className={styles.error}>
          Workspace context is unavailable. Sign in or select a workspace, then return to generate ad copy.
        </p>
      ) : null}
      {error ? <p role="alert" className={styles.error}>{error}</p> : null}
      {isGenerating ? <p role="status" className={styles.pending}>Generating ad copy from your brief…</p> : null}

      <Card>
        <form className={styles.form} onSubmit={(event) => void run(event)} aria-busy={isGenerating}>
          <div>
            <CardTitle sub="Use your own product and audience details. Required fields are sent only to the workspace-scoped generation endpoint.">
              Campaign brief
            </CardTitle>
          </div>
          <div className={styles.briefGrid}>
            <Field
              id="ads-product"
              label="Product or offer"
              value={product}
              onChange={(event) => setProduct(event.target.value)}
              placeholder="Describe the product or offer"
              minLength={2}
              maxLength={140}
              required
              disabled={isGenerating}
              autoComplete="off"
            />
            <Field
              id="ads-audience"
              label="Target audience"
              value={audience}
              onChange={(event) => setAudience(event.target.value)}
              placeholder="Who should this reach?"
              minLength={2}
              maxLength={120}
              required
              disabled={isGenerating}
              autoComplete="off"
            />
            <FieldSelect
              id="ads-platform"
              label="Advertising platform"
              value={platform}
              onChange={(event) => setPlatform(event.target.value)}
              required
              disabled={isGenerating}
            >
              <option value="" disabled>Choose a platform</option>
              <option value="google">Google</option>
              <option value="meta">Meta</option>
              <option value="linkedin">LinkedIn</option>
              <option value="tiktok">TikTok</option>
              <option value="instagram">Instagram</option>
              <option value="youtube">YouTube</option>
              <option value="facebook">Facebook</option>
              <option value="x">X</option>
              <option value="threads">Threads</option>
              <option value="snapchat">Snapchat</option>
            </FieldSelect>
            <FieldSelect
              id="ads-objective"
              label="Campaign objective"
              value={objective}
              onChange={(event) => setObjective(event.target.value)}
              required
              disabled={isGenerating}
            >
              <option value="" disabled>Choose an objective</option>
              <option value="traffic">Website traffic</option>
              <option value="leads">Lead generation</option>
              <option value="sales">Sales</option>
              <option value="awareness">Brand awareness</option>
            </FieldSelect>
          </div>
          <div className={styles.formActions}>
            <p className={styles.helper}>Review generated copy before using it in a live campaign.</p>
            <Button type="submit" variant="primary" disabled={!canGenerate || isGenerating}>
              {isGenerating ? 'Generating…' : 'Generate ad copy'}
            </Button>
          </div>
        </form>
      </Card>

      {result?.ai_status === 'fallback' ? (
        <p role="status" className={styles.notice}>
          The generation provider did not return AI-created copy. Its template fallback is hidden so it cannot be mistaken for generated content. Check the AI provider configuration and retry.
        </p>
      ) : null}

      {result?.ai_status === 'generated' ? (
        <Card>
          <div className={styles.resultHeader}>
            <div>
              <CardTitle sub={`${result.platform} · ${result.objective}`}>Generated ad copy</CardTitle>
              <div className={styles.metaRow}>
                <Badge tone="success">Provider generated</Badge>
                {result.provider_used || result.model_used ? (
                  <span className={styles.meta}>
                    {[result.provider_used, result.model_used].filter(Boolean).join(' · ')}
                  </span>
                ) : null}
              </div>
            </div>
            <Button type="button" variant="ghost" onClick={() => void copyGeneratedText()}>
              Copy ad copy
            </Button>
          </div>
          <pre className={styles.resultText}>{result.outputs.text}</pre>
          {copyStatus ? <p role="status" className={styles.helper}>{copyStatus}</p> : null}
        </Card>
      ) : null}
    </Page>
  );
}
