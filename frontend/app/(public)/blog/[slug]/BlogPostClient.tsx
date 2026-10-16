'use client';

import Link from 'next/link';
import { ArrowLeft, ArrowRight } from 'lucide-react';
import { motion } from 'framer-motion';
import { BLOG_POSTS } from '../posts';

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
}

interface BlogPostClientProps {
  post: typeof BLOG_POSTS[0];
}

export default function BlogPostClient({ post }: BlogPostClientProps) {
  const articleJsonLd = {
    '@context': 'https://schema.org',
    '@type': 'Article',
    headline: post.title,
    description: post.description,
    datePublished: post.date,
    author: { '@type': 'Organization', name: post.author },
    publisher: { '@type': 'Organization', name: 'Nuxtron' },
  };

  return (
    <>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(articleJsonLd) }} />

      <article className="mk-section mk-pt-hero">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-50px' }}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
          className="mk-container max-w-2xl stagger-children"
        >
          <Link href="/blog" className="mb-8 inline-flex items-center gap-1.5 text-sm font-semibold text-info-ink group">
            <ArrowLeft size={14} className="transition-transform group-hover:-translate-x-1" /> Back to blog
          </Link>

          <p className="text-xs font-bold uppercase tracking-widest text-info-ink">{post.category}</p>
          <h1 className="mt-3 text-4xl font-semibold tracking-tight text-info-ink sm:text-5xl">{post.title}</h1>
          <div className="mt-4 flex items-center gap-3 text-sm text-info">
            <span>{post.author}</span>
            <span aria-hidden="true">·</span>
            <time dateTime={post.date}>{formatDate(post.date)}</time>
            <span aria-hidden="true">·</span>
            <span>{post.readMinutes} min read</span>
          </div>

          <div className="mt-10 space-y-6 text-[17px] leading-relaxed text-info-ink">
            {post.paragraphs.map((paragraph, i) => (
              <motion.p
                key={i}
                initial={{ opacity: 0, y: 12 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: '-50px' }}
                transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1], delay: i * 0.08 }}
              >
                {paragraph}
              </motion.p>
            ))}
          </div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: '-50px' }}
            transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1], delay: 0.3 }}
            className="mt-14 rounded-2xl border border-line-soft bg-surface p-8 text-center group"
          >
            <h2 className="text-xl font-semibold text-info-ink">See it running on your data</h2>
            <Link href="/register" className="mk-shiny-cta mt-6 group">
              Start free <ArrowRight size={16} className="transition-transform group-hover:translate-x-1" />
            </Link>
          </motion.div>
        </motion.div>
      </article>
    </>
  );
}