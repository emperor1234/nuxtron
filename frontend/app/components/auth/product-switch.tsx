'use client';

import {
  createContext,
  useCallback,
  useContext,
  useId,
  useMemo,
  useState,
  useSyncExternalStore,
  type ReactNode,
} from 'react';
import { Check } from 'lucide-react';
import { getStoredProductLine } from '@/app/lib/api-client';
import {
  DEFAULT_PRODUCT_LINE,
  PRODUCT_LINES,
  PRODUCT_META,
  PRODUCT_QUERY_PARAM,
  parseProductLine,
  type ProductLine,
} from '@/app/lib/product-line';
import styles from './product-switch.module.css';

/**
 * Product choice on the sign-in and sign-up pages.
 *
 * Resolution order for the initial product: `?product=` (read by the server
 * page and passed in as `initialProduct`), then the product remembered from
 * the last sign-in, then the default. The stored value is read through
 * `useSyncExternalStore` with a `null` server snapshot, so the server markup
 * and the first client render always agree (no hydration mismatch).
 *
 * The choice is a sign-in mode, not an entitlement. It is sent to
 * /api/auth/session, which re-validates it; proxy.ts enforces it server-side.
 */

type AuthProductContextValue = {
  product: ProductLine;
  setProduct: (product: ProductLine) => void;
};

const AuthProductContext = createContext<AuthProductContextValue | null>(null);

function subscribeToNothing(): () => void {
  return () => {
    // The product never changes from outside this component.
  };
}

function readNothing(): ProductLine | null {
  return null;
}

/** Rewrites `?product=` in place, keeping every other parameter (e.g. `?next=`). */
function replaceProductInUrl(product: ProductLine): void {
  if (!globalThis.window) return;
  const url = new URL(globalThis.window.location.href);
  url.searchParams.set(PRODUCT_QUERY_PARAM, product);
  globalThis.window.history.replaceState(null, '', `${url.pathname}${url.search}${url.hash}`);
}

export function AuthProductProvider({
  initialProduct,
  children,
}: {
  initialProduct: ProductLine | null;
  children: ReactNode;
}) {
  const [chosen, setChosen] = useState<ProductLine | null>(() => parseProductLine(initialProduct));
  const stored = useSyncExternalStore(subscribeToNothing, getStoredProductLine, readNothing);
  const product = chosen ?? stored ?? DEFAULT_PRODUCT_LINE;

  const setProduct = useCallback((next: ProductLine) => {
    const parsed = parseProductLine(next);
    if (!parsed) return;
    setChosen(parsed);
    replaceProductInUrl(parsed);
  }, []);

  const value = useMemo(() => ({ product, setProduct }), [product, setProduct]);
  return <AuthProductContext.Provider value={value}>{children}</AuthProductContext.Provider>;
}

/** The product the visitor is signing in to. Must be used inside AuthProductProvider. */
export function useAuthProduct(): AuthProductContextValue {
  const value = useContext(AuthProductContext);
  if (!value) throw new Error('useAuthProduct must be used inside <AuthProductProvider>.');
  return value;
}

/** Renders the string for the currently selected product. */
export function ProductText({ text }: { text: Readonly<Record<ProductLine, string>> }) {
  const { product } = useAuthProduct();
  return <>{text[product]}</>;
}

/** Numbered list of points for the currently selected product. */
export function ProductPoints({ points }: { points: Readonly<Record<ProductLine, readonly string[]>> }) {
  const { product } = useAuthProduct();
  return (
    <ul>
      {points[product].map((point, index) => (
        <li key={point}>
          <span aria-hidden="true">{String(index + 1).padStart(2, '0')}</span>
          {point}
        </li>
      ))}
    </ul>
  );
}

/**
 * Two-option radio group: "Nuxtron SEO" / "Nuxtron Marketing".
 *
 * Native radio inputs give the full radiogroup keyboard model for free
 * (Tab into the group, arrow keys move and select) and announce correctly in
 * every screen reader; the visible card is the input's label.
 */
export function ProductSwitch({ legend }: { legend: string }) {
  const { product, setProduct } = useAuthProduct();
  const name = useId();

  return (
    <fieldset className={styles.group} role="radiogroup" aria-labelledby={`${name}-legend`}>
      <legend id={`${name}-legend`} className={styles.legend}>
        {legend}
      </legend>
      <div className={styles.options}>
        {PRODUCT_LINES.map((line) => {
          const meta = PRODUCT_META[line];
          const id = `${name}-${line}`;
          const selected = product === line;
          return (
            <div key={line} className={styles.option}>
              <input
                id={id}
                className={styles.input}
                type="radio"
                name={name}
                value={line}
                checked={selected}
                onChange={() => setProduct(line)}
                aria-describedby={`${id}-tagline`}
              />
              <label htmlFor={id} className={styles.card}>
                <span className={styles.head}>
                  <span className={styles.name}>{meta.name}</span>
                  <span className={styles.indicator} aria-hidden="true">
                    <Check size={12} strokeWidth={2.5} className={styles.check} />
                  </span>
                </span>
                <span id={`${id}-tagline`} className={styles.tagline}>
                  {meta.tagline}
                </span>
              </label>
            </div>
          );
        })}
      </div>
    </fieldset>
  );
}
