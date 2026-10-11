import type { Metadata, Route } from "next";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { parseProductLine, productAuthHref } from "@/app/lib/product-line";
import { FEATURE_JOBS, FEATURE_TOOLS, type ProductFilter } from "../_content/features";
import { RelatedProductVideo } from "../_components/sections/related-product-video";
import { FeaturesExplorer } from "./features-explorer";
import styles from "./features.module.css";

export const metadata: Metadata = {
  title: "Features | Nuxtron",
  description:
    "Every Nuxtron tool, organised by the job it does: research, create and optimize, track, and publish — across Nuxtron SEO and Nuxtron Marketing.",
  alternates: { canonical: "/features" },
};

const SEO_COUNT = FEATURE_TOOLS.filter((tool) => tool.product !== "marketing").length;
const MARKETING_COUNT = FEATURE_TOOLS.filter((tool) => tool.product !== "seo").length;

export default async function FeaturesPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const params = await searchParams;
  const product: ProductFilter = parseProductLine(params.product) ?? "all";
  const query = typeof params.q === "string" ? params.q.slice(0, 80) : "";

  return (
    <div className={styles.page}>
      <header className={styles.hero}>
        <p className={styles.eyebrow}>Features</p>
        <h1 className={styles.title}>
          Every tool, organised
          <span className={styles.accent}> by the job it does.</span>
        </h1>
        <p className={styles.intro}>
          Research the opportunity, create the work, track what moves and publish where it counts — across Nuxtron SEO
          and Nuxtron Marketing.
        </p>
        <dl className={styles.facts}>
          <div>
            <dt>Tools</dt>
            <dd>{FEATURE_TOOLS.length}</dd>
          </div>
          <div>
            <dt>In Nuxtron SEO</dt>
            <dd>{SEO_COUNT}</dd>
          </div>
          <div>
            <dt>In Nuxtron Marketing</dt>
            <dd>{MARKETING_COUNT}</dd>
          </div>
          <div>
            <dt>Jobs covered</dt>
            <dd>{FEATURE_JOBS.length}</dd>
          </div>
        </dl>
      </header>

      <FeaturesExplorer initialProduct={product} initialQuery={query} />
      <RelatedProductVideo product={product} />

      <section className={styles.cta} aria-labelledby="features-cta">
        <h2 id="features-cta">One account. Choose the product you need.</h2>
        <p>Start with search and AI visibility, or with content, social and customer work.</p>
        <div className={styles.ctaActions}>
          <Button asChild size="lg">
            <Link href={productAuthHref("/register", "seo") as Route}>
              Start with Nuxtron SEO <ArrowRight data-icon="inline-end" />
            </Link>
          </Button>
          <Button asChild size="lg" variant="outline" className={styles.ctaSecondary}>
            <Link href={productAuthHref("/register", "marketing") as Route}>Start with Nuxtron Marketing</Link>
          </Button>
        </div>
      </section>
    </div>
  );
}
