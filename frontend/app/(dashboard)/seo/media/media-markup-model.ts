export type MediaKind = 'image' | 'video';

export type MediaAsset = {
  id: string;
  kind: MediaKind;
  source: string | null;
  alt: string | null;
  width: string | null;
  height: string | null;
  loading: string | null;
  hasCaptionsTrack: boolean | null;
  hasPoster: boolean | null;
  hasAccessibleName: boolean | null;
  issues: string[];
};

export type MediaMarkupReview = {
  imageCount: number;
  videoCount: number;
  imagesMissingAlt: number;
  imagesWithEmptyAltReview: number;
  imagesMissingDimensions: number;
  videosWithoutCaptions: number;
  videosWithoutPoster: number;
  videosWithoutAccessibleName: number;
  findingCount: number;
  assets: MediaAsset[];
};

const MAX_MARKUP_LENGTH = 1_000_000;

function nullableAttribute(element: Element | null, name: string): string | null {
  if (!element) return null;
  const value = element.getAttribute(name);
  return value === null ? null : value.trim();
}

function videoSource(video: Element): string | null {
  return nullableAttribute(video, 'src')
    || nullableAttribute(video.querySelector('source'), 'src');
}

function mediaAssetIssues(assets: MediaAsset[]): number {
  return assets.reduce((total, asset) => total + asset.issues.length, 0);
}

export function parseMediaMarkup(markup: string): MediaMarkupReview {
  if (!markup.trim()) throw new Error('Paste page markup before reviewing media elements.');
  if (markup.length > MAX_MARKUP_LENGTH) throw new Error('Markup sample is too large. Limit it to 1 MB.');
  const Parser = globalThis.DOMParser;
  if (typeof Parser !== 'function') throw new Error('Local HTML parsing is unavailable in this browser.');

  const parsed = new Parser().parseFromString(markup, 'text/html');
  const assets: MediaAsset[] = [];
  let imageCount = 0;
  let videoCount = 0;

  for (const element of Array.from(parsed.querySelectorAll('img, video'))) {
    const tag = element.tagName.toLowerCase();
    if (tag === 'img') {
      imageCount += 1;
      const alt = nullableAttribute(element, 'alt');
      const width = nullableAttribute(element, 'width');
      const height = nullableAttribute(element, 'height');
      const decorative = element.getAttribute('role') === 'presentation'
        || element.getAttribute('aria-hidden') === 'true';
      const issues: string[] = [];
      if (alt === null && !decorative) issues.push('Alt attribute is missing from the supplied markup.');
      if (alt !== null && alt.length === 0 && !decorative) {
        issues.push('Alt text is empty; confirm this image is decorative.');
      }
      if (!width || !height) issues.push('Explicit width and height are not both present in the supplied markup.');
      assets.push({
        id: `image-${imageCount}`,
        kind: 'image',
        source: nullableAttribute(element, 'src') || nullableAttribute(element, 'srcset'),
        alt,
        width,
        height,
        loading: nullableAttribute(element, 'loading'),
        hasCaptionsTrack: null,
        hasPoster: null,
        hasAccessibleName: null,
        issues,
      });
      continue;
    }

    videoCount += 1;
    const hasCaptionsTrack = Array.from(element.querySelectorAll('track')).some((track) => {
      const kind = track.getAttribute('kind')?.toLowerCase();
      return kind === 'captions' || kind === 'subtitles';
    });
    const hasPoster = Boolean(nullableAttribute(element, 'poster'));
    const hasAccessibleName = Boolean(nullableAttribute(element, 'aria-label') || nullableAttribute(element, 'title'));
    const issues: string[] = [];
    if (!hasCaptionsTrack) issues.push('No captions or subtitles track was found in the supplied markup.');
    if (!hasPoster) issues.push('No poster image was specified in the supplied markup.');
    if (!hasAccessibleName) issues.push('No title or accessible name was found in the supplied markup.');
    assets.push({
      id: `video-${videoCount}`,
      kind: 'video',
      source: videoSource(element),
      alt: null,
      width: nullableAttribute(element, 'width'),
      height: nullableAttribute(element, 'height'),
      loading: null,
      hasCaptionsTrack,
      hasPoster,
      hasAccessibleName,
      issues,
    });
  }

  const images = assets.filter((asset) => asset.kind === 'image');
  const videos = assets.filter((asset) => asset.kind === 'video');
  return {
    imageCount,
    videoCount,
    imagesMissingAlt: images.filter((asset) => asset.alt === null && asset.issues.some((issue) => issue.startsWith('Alt attribute is missing'))).length,
    imagesWithEmptyAltReview: images.filter((asset) => asset.issues.some((issue) => issue.startsWith('Alt text is empty'))).length,
    imagesMissingDimensions: images.filter((asset) => asset.issues.some((issue) => issue.startsWith('Explicit width'))).length,
    videosWithoutCaptions: videos.filter((asset) => asset.hasCaptionsTrack === false).length,
    videosWithoutPoster: videos.filter((asset) => asset.hasPoster === false).length,
    videosWithoutAccessibleName: videos.filter((asset) => asset.hasAccessibleName === false).length,
    findingCount: mediaAssetIssues(assets),
    assets,
  };
}

function csvCell(value: string | null): string {
  const text = value ?? '';
  const safe = /^[\s]*[=+@-]/.test(text) ? `'${text}` : text;
  return `"${safe.replaceAll('"', '""')}"`;
}

export function mediaReviewCsv(review: MediaMarkupReview): string {
  const rows = [['Type', 'Source from supplied markup', 'Alt text', 'Width', 'Height', 'Loading', 'Captions track', 'Poster', 'Accessible name', 'Markup review notes']];
  for (const asset of review.assets) {
    rows.push([
      asset.kind,
      asset.source ?? '',
      asset.alt ?? '',
      asset.width ?? '',
      asset.height ?? '',
      asset.loading ?? '',
      asset.hasCaptionsTrack === null ? 'n/a' : asset.hasCaptionsTrack ? 'yes' : 'no',
      asset.hasPoster === null ? 'n/a' : asset.hasPoster ? 'yes' : 'no',
      asset.hasAccessibleName === null ? 'n/a' : asset.hasAccessibleName ? 'yes' : 'no',
      asset.issues.join('; '),
    ]);
  }
  return rows.map((row) => row.map(csvCell).join(',')).join('\r\n');
}
