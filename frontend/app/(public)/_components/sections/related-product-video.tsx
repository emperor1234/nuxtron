import type { ProductLine } from "@/app/lib/product-line";
import styles from "./related-product-video.module.css";

type ProductSelection = ProductLine | "all";

type Film = {
  product: ProductLine;
  name: string;
  title: string;
  description: string;
  src: string;
  poster: string;
};

const FILMS: Record<ProductLine, Film> = {
  seo: {
    product: "seo",
    name: "Nuxtron SEO",
    title: "Search signals, turned into next steps.",
    description:
      "Follow a discovery signal through an AI answer to the work worth doing next.",
    src: "/media/nuxtron-visibility-tour.mp4",
    poster: "/media/nuxtron-visibility-poster.jpg",
  },
  marketing: {
    product: "marketing",
    name: "Nuxtron Marketing",
    title: "From first brief to work in motion.",
    description:
      "Watch a brief become a creative, move onto the calendar, and return as a clear signal.",
    src: "/media/nuxtron-marketing-tour.mp4",
    poster: "/media/nuxtron-marketing-poster.jpg",
  },
};

export function RelatedProductVideo({
  product,
}: {
  product: ProductSelection;
}) {
  const products: readonly ProductLine[] =
    product === "all" ? ["seo", "marketing"] : [product];

  return (
    <section className={styles.section} aria-labelledby="product-films-title">
      <div className={styles.intro}>
        <h2 id="product-films-title" className={styles.title}>
          {products.length === 1
            ? "See the work move."
            : "Two products. One clear view."}
        </h2>
        <p className={styles.summary}>
          {products.length === 1
            ? "A short, silent product film. Press play when you are ready."
            : "Choose a workspace to preview. Both films are silent and play only when you press play."}
        </p>
      </div>

      <div className={styles.grid} data-count={products.length}>
        {products.map((key) => {
          const film = FILMS[key];
          const headingId = `product-film-${film.product}-heading`;
          const descriptionId = `product-film-${film.product}-description`;
          return (
            <article
              key={film.product}
              className={styles.card}
              data-product={film.product}
            >
              <div className={styles.copy}>
                <p className={styles.productName}>{film.name}</p>
                <h3 id={headingId} className={styles.cardTitle}>
                  {film.title}
                </h3>
                <p id={descriptionId} className={styles.cardDescription}>
                  {film.description}
                </p>
              </div>
              <figure className={styles.figure}>
                <video
                  className={styles.video}
                  controls
                  playsInline
                  muted
                  preload="none"
                  poster={film.poster}
                  aria-labelledby={headingId}
                  aria-describedby={descriptionId}
                >
                  <source src={film.src} type="video/mp4" />
                  Your browser does not support the Nuxtron product film.
                </video>
              </figure>
            </article>
          );
        })}
      </div>
    </section>
  );
}
