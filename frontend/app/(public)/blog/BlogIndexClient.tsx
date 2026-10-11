"use client";

import { useSyncExternalStore } from "react";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { motion, useReducedMotion } from "framer-motion";
import { BLOG_POSTS } from "./posts";

const subscribeToHydration = () => () => undefined;
const getHydratedSnapshot = () => true;
const getServerHydrationSnapshot = () => false;

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

function useHydratedReducedMotion() {
  const preference = useReducedMotion();
  const hydrated = useSyncExternalStore(
    subscribeToHydration,
    getHydratedSnapshot,
    getServerHydrationSnapshot,
  );

  return hydrated && preference;
}

function StaggeredPost({
  post,
  index,
}: {
  post: (typeof BLOG_POSTS)[0];
  index: number;
}) {
  const reduced = useHydratedReducedMotion();

  return (
    <motion.div
      initial={reduced ? { opacity: 0 } : { opacity: 0, y: 16 }}
      whileInView={reduced ? { opacity: 1 } : { opacity: 1, y: 0 }}
      transformTemplate={reduced ? () => "none" : undefined}
      viewport={{ once: true, margin: "-50px" }}
      transition={{
        duration: reduced ? 0.2 : 0.5,
        ease: reduced ? [0.23, 1, 0.32, 1] : [0.16, 1, 0.3, 1],
        delay: reduced ? 0 : index * 0.1,
      }}
    >
      <Link href={`/blog/${post.slug}`} className="mk-card block p-8 group">
        <p className="text-xs font-bold uppercase tracking-widest text-info-ink">
          {post.category}
        </p>
        <h2 className="mt-2 text-2xl font-semibold tracking-tight text-info-ink transition-colors group-hover:text-info-ink">
          {post.title}
        </h2>
        <p className="mt-3 text-[15px] leading-relaxed text-info-ink">
          {post.description}
        </p>
        <div className="mt-5 flex items-center gap-3 text-xs text-info">
          <time dateTime={post.date}>{formatDate(post.date)}</time>
          <span aria-hidden="true">·</span>
          <span>{post.readMinutes} min read</span>
          <span className="ml-auto inline-flex items-center gap-1 font-semibold text-info-ink transition-transform group-hover:translate-x-1">
            Read <ArrowRight size={14} />
          </span>
        </div>
      </Link>
    </motion.div>
  );
}

export default function BlogIndexClient() {
  const reduced = useHydratedReducedMotion();

  return (
    <section className="mk-section mk-pt-hero">
      <div className="mk-container max-w-3xl">
        <motion.div
          initial={reduced ? { opacity: 0 } : { opacity: 0, y: 20 }}
          whileInView={reduced ? { opacity: 1 } : { opacity: 1, y: 0 }}
          transformTemplate={reduced ? () => "none" : undefined}
          viewport={{ once: true, margin: "-50px" }}
          transition={{
            duration: reduced ? 0.2 : 0.6,
            ease: reduced ? [0.23, 1, 0.32, 1] : [0.16, 1, 0.3, 1],
          }}
        >
          <span className="mk-eyebrow mb-5">Blog</span>
          <h1 className="mb-4 text-4xl font-semibold tracking-tight text-info-ink sm:text-5xl">
            Notes on growth, AI, and security
          </h1>
          <p className="mb-12 text-lg leading-relaxed text-info-ink">
            Writing from the team building Nuxtron — on AI-visibility tracking,
            running a connected growth stack, and what supervised autonomy means
            in practice.
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
