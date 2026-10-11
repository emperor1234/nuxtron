import type { ReactNode } from 'react';
import { MarketingHeader } from '@/app/components/marketing/marketing-header';
import { MarketingFooter } from '@/app/components/marketing/marketing-footer';
import type { FeaturedPost } from '@/app/components/marketing/site-links';
import { BLOG_POSTS } from './blog/posts';
import './marketing.css';

const AUTH_ROUTES = ['/login', '/register', '/reset-password'];

/** Newest post for the Resources menu. Picked here on the server so the post
 * bodies in BLOG_POSTS never ship in the header's client bundle. */
function newestPost(): FeaturedPost | null {
  const [post] = [...BLOG_POSTS].sort((a, b) => b.date.localeCompare(a.date));
  if (!post) return null;
  const { slug, title, description, category, date, readMinutes } = post;
  return { slug, title, description, category, date, readMinutes };
}

export default function PublicLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <div className="mk-root">
      <a className="mk-skip" href="#main-content">
        Skip to content
      </a>
      <MarketingHeader featuredPost={newestPost()} />
      <main id="main-content" className="mk-main">
        {children}
      </main>
      <MarketingFooter authRoutes={AUTH_ROUTES} />
    </div>
  );
}
