import Link from "next/link";
import type { Route } from "next";
import { ArrowRight } from "lucide-react";
import { BLOG_POSTS, type BlogPost } from "../../blog/posts";
import type { ResearchContent } from "../../_content/types";
import { SectionHead } from "./section-head";
import styles from "./research-grid-section.module.css";

const TITLE_ID = "research-title";
const MAX_POSTS = 5;

const DATE_FORMAT = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
  year: "numeric",
  timeZone: "UTC",
});

/**
 * Newest real posts, with posts in the given categories first. When fewer
 * than `limit` match, the grid is filled with the newest of the rest, so one
 * matching post never sits alone in an otherwise empty grid.
 */
export function selectResearchPosts(
  posts: readonly BlogPost[],
  categories: readonly string[] | undefined,
  limit = MAX_POSTS,
): BlogPost[] {
  const newestFirst = [...posts].sort((a, b) => b.date.localeCompare(a.date));
  if (!categories?.length) return newestFirst.slice(0, limit);
  const wanted = new Set(categories);
  const matching = newestFirst.filter((post) => wanted.has(post.category));
  const others = newestFirst.filter((post) => !wanted.has(post.category));
  return [...matching, ...others].slice(0, limit);
}

/** Research and writing grid, built only from published posts. */
export function ResearchGridSection({ content }: { content: ResearchContent }) {
  const posts = selectResearchPosts(BLOG_POSTS, content.categories);
  if (posts.length === 0) return null;
  const [featured, ...rest] = posts;

  return (
    <section className={styles.section} aria-labelledby={TITLE_ID}>
      <div className={styles.inner}>
        <div className={styles.top}>
          <SectionHead id={TITLE_ID} eyebrow={content.eyebrow} title={content.title} intro={content.intro} />
          <Link href={content.cta.href as Route} className={styles.all}>
            {content.cta.label}
            <ArrowRight size={15} aria-hidden="true" />
          </Link>
        </div>
        <ul className={styles.grid}>
          {featured ? (
            <li className={styles.featuredItem}>
              <PostCard post={featured} featured />
            </li>
          ) : null}
          {rest.map((post) => (
            <li key={post.slug}>
              <PostCard post={post} />
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

function PostCard({ post, featured = false }: { post: BlogPost; featured?: boolean }) {
  return (
    <article className={styles.card} data-featured={featured}>
      <p className={styles.category}>{post.category}</p>
      <h3 className={styles.postTitle}>
        <Link href={`/blog/${post.slug}` as Route} className={styles.postLink}>
          {post.title}
        </Link>
      </h3>
      {featured ? <p className={styles.description}>{post.description}</p> : null}
      <p className={styles.meta}>
        <time dateTime={post.date}>{DATE_FORMAT.format(new Date(`${post.date}T00:00:00Z`))}</time>
        <span aria-hidden="true"> · </span>
        {post.readMinutes} min read
      </p>
    </article>
  );
}
