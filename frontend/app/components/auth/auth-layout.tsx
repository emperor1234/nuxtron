import { ArrowUpRight } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";
import type { ProductLine } from "@/app/lib/product-line";
import { AuthProductProvider, ProductPoints, ProductText } from "./product-switch";

/** Copy that changes with the product the visitor is signing in to. */
export type AuthProductCopy = Readonly<
  Record<
    ProductLine,
    {
      subheading: string;
      panelTitle: string;
      panelPoints: readonly string[];
    }
  >
>;

type StaticCopyProps = {
  subheading: string;
  panelTitle: string;
  panelPoints: readonly string[];
  initialProduct?: never;
  copy?: never;
};

type ProductCopyProps = {
  /** `?product=` from the page's searchParams, already narrowed (or null). */
  initialProduct: ProductLine | null;
  copy: AuthProductCopy;
  subheading?: never;
  panelTitle?: never;
  panelPoints?: never;
};

type AuthLayoutProps = { heading: string; children: ReactNode } & (StaticCopyProps | ProductCopyProps);

function pick<K extends keyof AuthProductCopy[ProductLine]>(copy: AuthProductCopy, key: K) {
  return { seo: copy.seo[key], marketing: copy.marketing[key] };
}

function StaticPoints({ points }: { points: readonly string[] }) {
  return (
    <ul>
      {points.map((point, index) => (
        <li key={point}>
          <span aria-hidden="true">{String(index + 1).padStart(2, "0")}</span>
          {point}
        </li>
      ))}
    </ul>
  );
}

/**
 * Server-rendered shell for the auth pages. With `copy` + `initialProduct`
 * (/login, /register) the product-aware pieces are small client islands that
 * read the product switch's context, so the copy follows the switch without
 * a navigation. With plain strings (/reset-password) it renders static copy.
 */
export function AuthLayout(props: AuthLayoutProps) {
  const { heading, children } = props;
  const productAware = props.copy !== undefined;

  const shell = (
    <div className="auth-surface">
      <div className="auth-composition">
        <section className="auth-story" aria-label="About Nuxtron">
          <p className="mk-eyebrow">YOUR CONNECTED WORKSPACE</p>
          <h2>{productAware ? <ProductText text={pick(props.copy, "panelTitle")} /> : props.panelTitle}</h2>
          {productAware ? (
            <ProductPoints points={pick(props.copy, "panelPoints")} />
          ) : (
            <StaticPoints points={props.panelPoints} />
          )}
          <Link href="/features">
            Explore the platform <ArrowUpRight size={16} aria-hidden="true" />
          </Link>
        </section>
        <section className="auth-form-panel" aria-labelledby="auth-heading">
          <h1 id="auth-heading">{heading}</h1>
          <p>{productAware ? <ProductText text={pick(props.copy, "subheading")} /> : props.subheading}</p>
          <div className="auth-fields">{children}</div>
        </section>
      </div>
    </div>
  );

  return productAware ? (
    <AuthProductProvider initialProduct={props.initialProduct}>{shell}</AuthProductProvider>
  ) : (
    shell
  );
}
export function AuthSubmit({
  busy,
  children,
}: {
  busy: boolean;
  children: ReactNode;
}) {
  return (
    <button
      type="submit"
      disabled={busy}
      aria-busy={busy}
      className="auth-submit"
    >
      {children}
    </button>
  );
}
export function AuthAltLinks({ children }: { children: ReactNode }) {
  return <p className="auth-alt-links">{children}</p>;
}
export const authLink = "auth-link";
