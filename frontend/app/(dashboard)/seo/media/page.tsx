'use client';

import { useMemo, useState, type FormEvent } from 'react';
import { Badge, Button, Card, CardTitle, Page, PageHeader } from '../../_ui/kit';
import { mediaReviewCsv, parseMediaMarkup, type MediaAsset, type MediaKind, type MediaMarkupReview } from './media-markup-model';
import styles from './media-markup.module.css';

type AssetFilter = 'all' | MediaKind | 'with-findings';

export default function MediaMarkupReviewPage() {
  const [sourceLabel, setSourceLabel] = useState('');
  const [markup, setMarkup] = useState('');
  const [filter, setFilter] = useState<AssetFilter>('all');
  const [review, setReview] = useState<MediaMarkupReview | null>(null);
  const [error, setError] = useState('');

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError('');
    setReview(null);
    try {
      setReview(parseMediaMarkup(markup));
      setFilter('all');
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not review the supplied markup.');
    }
  }

  const visibleAssets = useMemo(() => {
    if (!review) return [];
    if (filter === 'with-findings') return review.assets.filter((asset) => asset.issues.length > 0);
    if (filter === 'all') return review.assets;
    return review.assets.filter((asset) => asset.kind === filter);
  }, [filter, review]);

  function exportCsv() {
    if (!review) return;
    const href = URL.createObjectURL(new Blob([mediaReviewCsv(review)], { type: 'text/csv;charset=utf-8' }));
    const anchor = document.createElement('a');
    anchor.href = href;
    anchor.download = 'media-markup-review.csv';
    anchor.click();
    URL.revokeObjectURL(href);
  }

  function renderFact(label: string, value: string | null) {
    return <span key={label}>{label}: {value || 'not specified'}</span>;
  }

  function renderAsset(asset: MediaAsset, index: number) {
    return (
      <li className={styles.asset} key={asset.id}>
        <div className={styles.assetTop}>
          <h3 className={styles.assetTitle}>{asset.kind === 'image' ? 'Image' : 'Video'} element {index + 1}</h3>
          <Badge tone={asset.issues.length ? 'danger' : 'success'}>
            {asset.issues.length ? `${asset.issues.length} markup ${asset.issues.length === 1 ? 'check' : 'checks'}` : 'No markup issues identified'}
          </Badge>
        </div>
        <div className={styles.source}>Source in supplied markup: <code>{asset.source || 'No src/srcset provided'}</code></div>
        <div className={styles.facts}>
          {asset.kind === 'image' ? <>
            {renderFact('Alt', asset.alt === null ? null : asset.alt === '' ? '(empty)' : asset.alt)}
            {renderFact('Width', asset.width)}
            {renderFact('Height', asset.height)}
            {renderFact('Loading', asset.loading)}
          </> : <>
            {renderFact('Captions/subtitles track', asset.hasCaptionsTrack === null ? null : asset.hasCaptionsTrack ? 'present' : 'not found')}
            {renderFact('Poster', asset.hasPoster === null ? null : asset.hasPoster ? 'specified' : 'not specified')}
            {renderFact('Accessible name', asset.hasAccessibleName === null ? null : asset.hasAccessibleName ? 'present' : 'not found')}
          </>}
        </div>
        {asset.issues.length > 0 ? <ul className={styles.issues}>{asset.issues.map((issue) => <li key={issue}>{issue}</li>)}</ul> : <p className={styles.empty}>No markup checks were triggered for this element. This is not a full-page accessibility or SEO certification.</p>}
      </li>
    );
  }

  return (
    <Page>
      <PageHeader
        title="Media Markup Review"
        subtitle="Inspect image and video attributes in HTML you provide. The sample is parsed locally in your browser."
      />

      <Card>
        <Badge tone="neutral">Local review · no page fetch</Badge>
        <p className={styles.scopeNote}>Paste the relevant HTML markup below. Nothing is sent to Nuxtron and no website or asset is fetched. Counts cover only the markup you provide; file size, compression, CSS background images, video sitemap, and transcript coverage are not measured here.</p>
        <form className={styles.form} onSubmit={handleSubmit}>
          <label className={styles.field} htmlFor="media-source-label">
            <span>Page URL or source label <em>(optional context only; it will not be opened)</em></span>
            <input id="media-source-label" type="text" value={sourceLabel} maxLength={500} onChange={(event) => setSourceLabel(event.target.value)} />
          </label>
          <label className={styles.field} htmlFor="media-markup">
            <span>HTML markup sample <b aria-label="required">Required</b></span>
            <textarea id="media-markup" value={markup} onChange={(event) => setMarkup(event.target.value)} rows={12} maxLength={1_000_000} required spellCheck={false} />
            <small>Up to 1 MB. Include the image and video elements you want to review. Scripts are not executed; only markup attributes are inspected.</small>
          </label>
          {error && <p className={styles.error} role="alert">{error}</p>}
          <Button type="submit" variant="primary">Review supplied markup</Button>
        </form>
      </Card>

      {review && (
        <section aria-label="Media markup review results">
          <Card>
            <CardTitle sub={sourceLabel.trim() ? `Context label: ${sourceLabel.trim()}` : 'Source: pasted markup only · no external page was requested'}>Observed markup</CardTitle>
            <div className={styles.metrics}>
              <div className={styles.metric}><span className={styles.metricName}>Images in sample</span><output aria-label="Images in supplied markup">{review.imageCount}</output></div>
              <div className={styles.metric}><span className={styles.metricName}>Videos in sample</span><output aria-label="Videos in supplied markup">{review.videoCount}</output></div>
              <div className={styles.metric}><span className={styles.metricName}>Images missing alt attribute</span><output aria-label="Images missing alt">{review.imagesMissingAlt}</output></div>
              <div className={styles.metric}><span className={styles.metricName}>Images with empty alt to review</span><output aria-label="Images with empty alt">{review.imagesWithEmptyAltReview}</output></div>
              <div className={styles.metric}><span className={styles.metricName}>Images without both dimensions</span><output aria-label="Images missing dimensions">{review.imagesMissingDimensions}</output></div>
              <div className={styles.metric}><span className={styles.metricName}>Videos without captions/subtitles tracks</span><output aria-label="Videos without captions">{review.videosWithoutCaptions}</output></div>
            </div>
            <p className={styles.scopeNote}>Video sitemap and transcript coverage: not assessed from this markup sample. An empty result means no matching tags were found in the supplied text, not that the full website has none.</p>
          </Card>

          <Card>
            <div className={styles.queueHeader}>
              <CardTitle sub={`${review.findingCount} markup checks across ${review.assets.length} observed media elements`}>Asset review queue</CardTitle>
              <label className={styles.filter} htmlFor="media-filter">
                <span>Filter assets</span>
                <select id="media-filter" value={filter} onChange={(event) => setFilter(event.target.value as AssetFilter)}>
                  <option value="all">All supplied assets</option>
                  <option value="image">Images</option>
                  <option value="video">Videos</option>
                  <option value="with-findings">Elements with markup checks</option>
                </select>
              </label>
            </div>
            {review.assets.length === 0 ? <p className={styles.empty}>No image or video elements were found in this supplied markup sample.</p> : visibleAssets.length === 0 ? <p className={styles.empty}>No supplied elements match this filter.</p> : (
              <ol className={styles.assetList}>{visibleAssets.map((asset) => renderAsset(asset, review.assets.indexOf(asset)))}</ol>
            )}
            {review.assets.length > 0 && (
              <div className={styles.exportRow}>
                <p className={styles.scopeNote}>Export contains only values extracted from the supplied markup and local review notes.</p>
                <Button type="button" onClick={exportCsv}>Export CSV</Button>
              </div>
            )}
          </Card>
        </section>
      )}
    </Page>
  );
}
