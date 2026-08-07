import type { Metadata } from 'next';
import Link from 'next/link';
import { notFound } from 'next/navigation';
import { ArrowLeft, ArrowRight } from 'lucide-react';
import { BLOG_POSTS, getPostBySlug } from '../posts';

export function generateStaticParams() {
  return BLOG_POSTS.map((post) => ({ slug: post.slug }));
}

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
  const { slug } = await params;
  const post = getPostBySlug(slug);
  if (!post) {
    return { title: 'Post not found | Nuxtron' };
  }
  return {
    title: `${post.title} | Nuxtron Blog`,
    description: post.description,
    alternates: { canonical: `/blog/${post.slug}` },
    openGraph: {
      title: post.title,
      description: post.description,
      type: 'article',
      publishedTime: post.date,
    },
  };
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
}

export default async function BlogPostPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const post = getPostBySlug(slug);
  if (!post) {
    notFound();
  }

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

      <article className="mk-section pt-40">
        <div className="mk-container max-w-2xl">
          <Link href="/blog" className="mb-8 inline-flex items-center gap-1.5 text-sm font-semibold text-[#0c8fcc]">
            <ArrowLeft size={14} /> Back to blog
          </Link>

          <p className="text-xs font-bold uppercase tracking-widest text-[#0c8fcc]">{post.category}</p>
          <h1 className="mt-3 text-4xl font-semibold tracking-tight text-[#0b1b2b] sm:text-5xl">{post.title}</h1>
          <div className="mt-4 flex items-center gap-3 text-sm text-[#8595a8]">
            <span>{post.author}</span>
            <span aria-hidden="true">·</span>
            <time dateTime={post.date}>{formatDate(post.date)}</time>
            <span aria-hidden="true">·</span>
            <span>{post.readMinutes} min read</span>
          </div>

          <div className="mt-10 space-y-6 text-[17px] leading-relaxed text-[#33475b]">
            {post.paragraphs.map((paragraph, i) => (
              <p key={i}>{paragraph}</p>
            ))}
          </div>

          <div className="mt-14 rounded-2xl border border-[#dbe6ee] bg-[#f6fafd] p-8 text-center">
            <h2 className="text-xl font-semibold text-[#0b1b2b]">See it running on your data</h2>
            <Link href="/register" className="mk-shiny-cta mt-6">
              Start free <ArrowRight size={16} />
            </Link>
          </div>
        </div>
      </article>
    </>
  );
}
