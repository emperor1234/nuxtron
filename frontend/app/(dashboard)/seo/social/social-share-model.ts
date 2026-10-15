export const SHARE_CHANNELS = ['x', 'facebook', 'linkedin', 'pinterest'] as const;
export type ShareChannel = (typeof SHARE_CHANNELS)[number];
export type SocialCardType = 'summary' | 'summary_large_image';

export type SocialShareInput = {
  channels: ShareChannel[];
  openGraphTitle: string;
  openGraphDescription: string;
  canonicalUrl: string;
  openGraphUrl: string;
  openGraphImage: string;
  twitterTitle: string;
  twitterDescription: string;
  twitterImage: string;
  twitterCardType: string;
};

export type SocialSharePreview = {
  channel: ShareChannel;
  title: string;
  description: string;
  imageUrl: string | null;
  pageUrl: string;
  titleSource: string;
  descriptionSource: string;
  imageSource: string;
  cardType: SocialCardType | null;
};

export type SocialShareReport = {
  previews: SocialSharePreview[];
  canonicalAlignment: 'not-provided' | 'match' | 'mismatch';
  canonicalUrl: string;
  openGraphUrl: string | null;
};

const CHANNEL_LABELS: Record<ShareChannel, string> = {
  x: 'X (Twitter)',
  facebook: 'Facebook',
  linkedin: 'LinkedIn',
  pinterest: 'Pinterest',
};

export function shareChannelLabel(channel: ShareChannel): string {
  return CHANNEL_LABELS[channel];
}

function absoluteHttpUrl(value: string, fieldName: string, optional = false): URL | null {
  const trimmed = value.trim();
  if (!trimmed && optional) return null;
  if (!trimmed) throw new Error(`${fieldName} is required.`);
  let parsed: URL;
  try {
    parsed = new URL(trimmed);
  } catch {
    throw new Error(`${fieldName} must be a complete HTTP or HTTPS URL.`);
  }
  if ((parsed.protocol !== 'http:' && parsed.protocol !== 'https:') || parsed.username || parsed.password) {
    throw new Error(`${fieldName} must use HTTP or HTTPS and must not include login credentials.`);
  }
  parsed.hash = '';
  return parsed;
}

function normalizedUrl(url: URL): string {
  return `${url.protocol}//${url.host}${url.pathname}${url.search}`;
}

export function buildSocialShareReport(input: SocialShareInput): SocialShareReport {
  if (!Array.isArray(input.channels) || input.channels.length === 0) {
    throw new Error('Select at least one channel to preview.');
  }
  if (input.channels.some((channel) => !SHARE_CHANNELS.includes(channel))) {
    throw new Error('One or more selected channels are not supported.');
  }
  const channels = [...new Set(input.channels)];
  const openGraphTitle = input.openGraphTitle.trim();
  const openGraphDescription = input.openGraphDescription.trim();
  if (!openGraphTitle) throw new Error('Open Graph title is required.');
  if (openGraphTitle.length > 300) throw new Error('Open Graph title must be 300 characters or fewer.');
  if (!openGraphDescription) throw new Error('Open Graph description is required.');
  if (openGraphDescription.length > 1000) throw new Error('Open Graph description must be 1,000 characters or fewer.');

  const canonicalUrl = absoluteHttpUrl(input.canonicalUrl, 'Canonical URL');
  if (!canonicalUrl) throw new Error('Canonical URL is required.');
  const openGraphUrl = absoluteHttpUrl(input.openGraphUrl, 'Open Graph URL', true);
  const openGraphImage = absoluteHttpUrl(input.openGraphImage, 'Open Graph image URL', true);
  const twitterImage = absoluteHttpUrl(input.twitterImage, 'Twitter image URL', true);
  const twitterTitle = input.twitterTitle.trim();
  const twitterDescription = input.twitterDescription.trim();
  if (twitterTitle.length > 300) throw new Error('Twitter title must be 300 characters or fewer.');
  if (twitterDescription.length > 1000) throw new Error('Twitter description must be 1,000 characters or fewer.');

  let twitterCardType: SocialCardType | null = null;
  if (channels.includes('x')) {
    if (input.twitterCardType !== 'summary' && input.twitterCardType !== 'summary_large_image') {
      throw new Error('Choose a Twitter card type when X (Twitter) is selected.');
    }
    twitterCardType = input.twitterCardType;
  }

  const previews = channels.map((channel): SocialSharePreview => {
    const isX = channel === 'x';
    const title = isX && twitterTitle ? twitterTitle : openGraphTitle;
    const description = isX && twitterDescription ? twitterDescription : openGraphDescription;
    const image = isX ? twitterImage ?? openGraphImage : openGraphImage;
    return {
      channel,
      title,
      description,
      imageUrl: image?.href ?? null,
      pageUrl: openGraphUrl?.href ?? canonicalUrl.href,
      titleSource: isX && twitterTitle ? 'Twitter title override' : 'Open Graph title',
      descriptionSource: isX && twitterDescription ? 'Twitter description override' : 'Open Graph description',
      imageSource: isX && twitterImage ? 'Twitter image override' : openGraphImage ? 'Open Graph image' : 'No image URL supplied',
      cardType: isX ? twitterCardType : null,
    };
  });

  const canonicalAlignment = openGraphUrl === null
    ? 'not-provided'
    : normalizedUrl(canonicalUrl) === normalizedUrl(openGraphUrl) ? 'match' : 'mismatch';

  return { previews, canonicalAlignment, canonicalUrl: canonicalUrl.href, openGraphUrl: openGraphUrl?.href ?? null };
}
