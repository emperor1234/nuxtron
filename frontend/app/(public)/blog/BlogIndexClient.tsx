'use client';

import Link from 'next/link';
import { ArrowRight } from 'lucide-react';
import { motion } from 'framer-motion';
import { BLOG_POSTS } from './posts';

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
}

function StaggeredPost({ post, index }: { post: typeof BLOG_POSTS[0]; index: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-50px' }}
      transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1], delay: index * 0.1 }}
    >
      <Link href={`/blog/${post.slug}`} className="mk-card block p-8 group">
        <p className="text-xs font-bold uppercase tracking-widest text-[#0c8fcc]">{post.category}</p>
        <h2 className="mt-2 text-2xl font-semibold tracking-tight text-[#0b1b2b] transition-colors group-hover:text-[#0c8fcc]">{post.title}</h2>
        <p className="mt-3 text-[15px] leading-relaxed text-[#55677c]">{post.description}</p>
        <div className="mt-5 flex items-center gap-3 text-xs text-[#8595a8]">
          <time dateTime={post.date}>{formatDate(post.date)}</time>
          <span aria-hidden="true">·</span>
          <span>{post.readMinutes} min read</span>
          <span className="ml-auto inline-flex items-center gap-1 font-semibold text-[#0ea5e9] transition-transform group-hover:translate-x-1">
            Read <ArrowRight size={14} />
          </span>
        </div>
      </Link>
    </motion.div>
  );
}

export default function BlogIndexClient() {
  return (
    <section className="mk-section mk-pt-hero">
      <div className="mk-container max-w-3xl">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-50px' }}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
        >
          <span className="mk-eyebrow mb-5">Blog</span>
          <h1 className="mb-4 text-4xl font-semibold tracking-tight text-[#0b1b2b] sm:text-5xl">
            Notes on growth, AI, and security
          </h1>
          <p className="mb-12 text-lg leading-relaxed text-[#55677c]">
            Writing from the team building Nuxtron — on AI-visibility tracking, running a connected growth stack, and
            what supervised autonomy means in practice.
          </p>
        </motion.div>

        <div className="space-y-6">
          {BLOG_POSTS.map((post, index) => (
            <StaggeredPost key={post.slug} post={post} index={index} />
          ))}
        </div>
      </div>
    </section>
  );
}