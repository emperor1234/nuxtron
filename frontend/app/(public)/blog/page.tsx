import type { Metadata } from 'next';
import Link from 'next/link';
import { ArrowRight } from 'lucide-react';
import { BLOG_POSTS } from './posts';

export const metadata: Metadata = {
  title: 'Blog | Nuxtron',
  description: 'Notes on AI visibility, running a connected growth stack, and building supervised autonomous agents.',
  alternates: { canonical: '/blog' },
};

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
}

export default function BlogIndexPage() {
  return (
    <section className="mk-section mk-pt-hero">
      <div className="mk-container max-w-3xl">
        <span className="mk-eyebrow mb-5">Blog</span>
        <h1 className="mb-4 text-4xl font-semibold tracking-tight text-[#0b1b2b] sm:text-5xl">
          Notes on growth, AI, and security
        </h1>
        <p className="mb-12 text-lg leading-relaxed text-[#55677c]">
          Writing from the team building Nuxtron — on AI-visibility tracking, running a connected growth stack, and
          what supervised autonomy means in practice.
        </p>

        <div className="space-y-6">
          {BLOG_POSTS.map((post) => (
            <Link key={post.slug} href={`/blog/${post.slug}`} className="mk-card block p-8">
              <p className="text-xs font-bold uppercase tracking-widest text-[#0c8fcc]">{post.category}</p>
              <h2 className="mt-2 text-2xl font-semibold tracking-tight text-[#0b1b2b]">{post.title}</h2>
              <p className="mt-3 text-[15px] leading-relaxed text-[#55677c]">{post.description}</p>
              <div className="mt-5 flex items-center gap-3 text-xs text-[#8595a8]">
                <time dateTime={post.date}>{formatDate(post.date)}</time>
                <span aria-hidden="true">·</span>
                <span>{post.readMinutes} min read</span>
                <span className="ml-auto inline-flex items-center gap-1 font-semibold text-[#0ea5e9]">
                  Read <ArrowRight size={14} />
                </span>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </section>
  );
}
