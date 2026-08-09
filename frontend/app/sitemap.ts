import type { MetadataRoute } from 'next';
import { BLOG_POSTS } from './(public)/blog/posts';

function siteUrl(): string {
  return (
    process.env.NEXT_PUBLIC_SITE_URL ||
    process.env.NEXT_PUBLIC_APP_URL ||
    (process.env.VERCEL_URL ? `https://${process.env.VERCEL_URL}` : 'http://localhost:4173')
  ).replace(/\/$/, '');
}

// Public, indexable marketing routes. Auth/dashboard/account routes are
// intentionally excluded (gated, non-indexable).
const PUBLIC_ROUTES: Array<{
  path: string;
  priority: number;
  changeFrequency: MetadataRoute.Sitemap[number]['changeFrequency'];
}> = [
  { path: '/', priority: 1.0, changeFrequency: 'weekly' },
  { path: '/features', priority: 0.9, changeFrequency: 'weekly' },
  { path: '/pricing', priority: 0.9, changeFrequency: 'weekly' },
  { path: '/integrations', priority: 0.7, changeFrequency: 'monthly' },
  { path: '/case-studies', priority: 0.6, changeFrequency: 'monthly' },
  { path: '/about', priority: 0.6, changeFrequency: 'monthly' },
  { path: '/careers', priority: 0.5, changeFrequency: 'weekly' },
  { path: '/contact', priority: 0.6, changeFrequency: 'monthly' },
  { path: '/trust', priority: 0.6, changeFrequency: 'monthly' },
  { path: '/faq', priority: 0.6, changeFrequency: 'monthly' },
  { path: '/changelog', priority: 0.5, changeFrequency: 'weekly' },
  { path: '/blog', priority: 0.6, changeFrequency: 'weekly' },
  { path: '/tools/translation-studio', priority: 0.4, changeFrequency: 'monthly' },
  { path: '/privacy', priority: 0.3, changeFrequency: 'yearly' },
  { path: '/terms', priority: 0.3, changeFrequency: 'yearly' },
];

export default function sitemap(): MetadataRoute.Sitemap {
  const base = siteUrl();
  const lastModified = new Date();

  const staticEntries = PUBLIC_ROUTES.map(({ path, priority, changeFrequency }) => ({
    url: `${base}${path}`,
    lastModified,
    changeFrequency,
    priority,
  }));

  const blogEntries = BLOG_POSTS.map((post) => ({
    url: `${base}/blog/${post.slug}`,
    lastModified: new Date(post.date),
    changeFrequency: 'monthly' as const,
    priority: 0.5,
  }));

  return [...staticEntries, ...blogEntries];
}
