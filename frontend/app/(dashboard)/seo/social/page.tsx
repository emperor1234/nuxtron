'use client';

import { useState, type FormEvent } from 'react';
import { Badge, Button, Card, CardTitle, Page, PageHeader } from '../../_ui/kit';
import { buildSocialShareReport, SHARE_CHANNELS, shareChannelLabel, type ShareChannel, type SocialShareInput, type SocialShareReport } from './social-share-model';
import styles from './social-share.module.css';

const INITIAL_INPUT: SocialShareInput = {
  channels: [],
  openGraphTitle: '',
  openGraphDescription: '',
  canonicalUrl: '',
  openGraphUrl: '',
  openGraphImage: '',
  twitterTitle: '',
  twitterDescription: '',
  twitterImage: '',
  twitterCardType: '',
};

export default function SocialSharePreviewPage() {
  const [input, setInput] = useState<SocialShareInput>(INITIAL_INPUT);
  const [report, setReport] = useState<SocialShareReport | null>(null);
  const [error, setError] = useState('');
  const [announcement, setAnnouncement] = useState('');

  function updateField<Key extends keyof SocialShareInput>(key: Key, value: SocialShareInput[Key]) {
    setInput((current) => ({ ...current, [key]: value }));
    setReport(null);
    setError('');
    setAnnouncement('');
  }

  function toggleChannel(channel: ShareChannel, checked: boolean) {
    const channels = checked
      ? [...input.channels, channel]
      : input.channels.filter((item) => item !== channel);
    updateField('channels', channels);
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError('');
    try {
      const nextReport = buildSocialShareReport(input);
      setReport(nextReport);
      setAnnouncement('Preview built locally from the metadata you supplied.');
    } catch (reason) {
      setReport(null);
      setError(reason instanceof Error ? reason.message : 'Could not build this share preview.');
    }
  }

  const canonicalStatus = report?.canonicalAlignment === 'match'
    ? 'Open Graph URL matches the supplied canonical URL.'
    : report?.canonicalAlignment === 'mismatch'
      ? 'Open Graph URL differs from the supplied canonical URL; review both values.'
      : 'Open Graph URL was not supplied; alignment is unknown.';

  return (
    <Page>
      <PageHeader title="Social Share Preview" subtitle="Draft channel-specific share cards from metadata you provide before distributing a page." />
      <Card>
        <Badge tone="neutral">Local preview · no crawl</Badge>
        <p className={styles.scopeNotice}>No page is fetched, and no platform preview service is contacted. The cards below are text previews calculated from these fields only; image URLs are shown as references and are not loaded. They do not guarantee how a third-party app will render the page.</p>
        <form className={styles.form} onSubmit={handleSubmit}>
          <fieldset className={styles.channels}>
            <legend>Preview channels <span>(select at least one)</span></legend>
            <div className={styles.channelOptions}>
              {SHARE_CHANNELS.map((channel) => (
                <label className={styles.channelOption} key={channel}>
                  <input type="checkbox" checked={input.channels.includes(channel)} onChange={(event) => toggleChannel(channel, event.target.checked)} />
                  {shareChannelLabel(channel)}
                </label>
              ))}
            </div>
          </fieldset>

          <div className={styles.fields}>
            <label className={styles.field} htmlFor="og-title">
              <span>Open Graph title <b>Required</b></span>
              <input id="og-title" value={input.openGraphTitle} maxLength={300} onChange={(event) => updateField('openGraphTitle', event.target.value)} required />
            </label>
            <label className={styles.field} htmlFor="canonical-url">
              <span>Canonical URL <b>Required</b></span>
              <input id="canonical-url" type="url" value={input.canonicalUrl} onChange={(event) => updateField('canonicalUrl', event.target.value)} required />
            </label>
            <label className={styles.field} htmlFor="og-description">
              <span>Open Graph description <b>Required</b></span>
              <textarea id="og-description" rows={3} maxLength={1000} value={input.openGraphDescription} onChange={(event) => updateField('openGraphDescription', event.target.value)} required />
            </label>
            <label className={styles.field} htmlFor="og-url">
              <span>Open Graph URL <small>(optional)</small></span>
              <input id="og-url" type="url" value={input.openGraphUrl} onChange={(event) => updateField('openGraphUrl', event.target.value)} />
            </label>
            <label className={styles.field} htmlFor="og-image">
              <span>Open Graph image URL <small>(optional, not fetched)</small></span>
              <input id="og-image" type="url" value={input.openGraphImage} onChange={(event) => updateField('openGraphImage', event.target.value)} />
            </label>
            <label className={styles.field} htmlFor="twitter-title">
              <span>X (Twitter) title override <small>(optional)</small></span>
              <input id="twitter-title" value={input.twitterTitle} maxLength={300} onChange={(event) => updateField('twitterTitle', event.target.value)} />
            </label>
            <label className={styles.field} htmlFor="twitter-description">
              <span>X (Twitter) description override <small>(optional)</small></span>
              <textarea id="twitter-description" rows={3} maxLength={1000} value={input.twitterDescription} onChange={(event) => updateField('twitterDescription', event.target.value)} />
            </label>
            <label className={styles.field} htmlFor="twitter-image">
              <span>X (Twitter) image URL override <small>(optional, not fetched)</small></span>
              <input id="twitter-image" type="url" value={input.twitterImage} onChange={(event) => updateField('twitterImage', event.target.value)} />
            </label>
            <label className={styles.field} htmlFor="twitter-card-type">
              <span>X (Twitter) card type <small>(required when X is selected)</small></span>
              <select id="twitter-card-type" value={input.twitterCardType} onChange={(event) => updateField('twitterCardType', event.target.value)}>
                <option value="">Choose a card type…</option>
                <option value="summary">Summary</option>
                <option value="summary_large_image">Summary with large image</option>
              </select>
            </label>
          </div>
          {error && <p className={styles.error} role="alert">{error}</p>}
          <Button type="submit" variant="primary">Build local preview</Button>
        </form>
      </Card>

      <p className={styles.status} role="status" aria-live="polite">{announcement}</p>

      {report && (
        <section aria-label="Social share previews">
          <Card>
            <CardTitle sub="This comparison uses only the canonical and Open Graph URLs entered above; neither page was opened.">Canonical alignment</CardTitle>
            <p className={styles.alignment}>{canonicalStatus}</p>
            <p className={styles.previewUrl}>Canonical URL: {report.canonicalUrl}</p>
            <p className={styles.previewUrl}>Open Graph URL: {report.openGraphUrl ?? 'not supplied'}</p>
          </Card>
          <Card>
            <CardTitle sub="Text-only previews; external images are not loaded and rendering can vary by platform.">Selected channel previews</CardTitle>
            <div className={styles.previews}>
              {report.previews.map((preview) => (
                <article className={styles.preview} key={preview.channel}>
                  <div className={styles.checkTop}>
                    <h3>{shareChannelLabel(preview.channel)}</h3>
                    <Badge tone="neutral">User-entered metadata</Badge>
                  </div>
                  {preview.cardType && <p className={styles.previewUrl}>Card type: {preview.cardType === 'summary_large_image' ? 'Summary with large image' : 'Summary'}</p>}
                  <p className={styles.previewTitle}>{preview.title}</p>
                  <p className={styles.previewDescription}>{preview.description}</p>
                  <p className={styles.previewUrl}>{preview.pageUrl}</p>
                  <p className={styles.sourceLabel}>Title source: {preview.titleSource} · Description source: {preview.descriptionSource}</p>
                  <p className={styles.imageReference}>{preview.imageUrl ? `Image URL reference (not fetched): ${preview.imageUrl}` : 'No image URL supplied.'}</p>
                  <p className={styles.sourceLabel}>Image source: {preview.imageSource}</p>
                </article>
              ))}
            </div>
          </Card>
        </section>
      )}
    </Page>
  );
}
