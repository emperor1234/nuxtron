"use client";

import { useState, type ComponentProps } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeftRight, X } from "lucide-react";
import { PRODUCT_META, productAuthHref } from "@/app/lib/product-line";
import {
  signOutAndNavigate,
  unavailableProductFrom,
  useProductLine,
} from "@/app/lib/use-product-line";
import { Card } from "../../_ui/kit";
import styles from "./product-unavailable-notice.module.css";

/**
 * Shown on /dashboard when proxy.ts bounced a deep link that belongs to the
 * other product (`?unavailable=<seo|marketing>`). It says plainly why the page
 * did not open and offers the one way in: signing in to that product.
 */
export default function ProductUnavailableNotice({
  requested,
}: {
  /** Raw `?unavailable=` value; validated here, never trusted. */
  requested: string | string[] | undefined;
}) {
  const router = useRouter();
  const current = useProductLine();
  const [dismissed, setDismissed] = useState(false);
  const [leaving, setLeaving] = useState(false);
  const target = unavailableProductFrom(requested, current);

  if (!target || !current || dismissed) return null;

  const targetMeta = PRODUCT_META[target];
  const currentMeta = PRODUCT_META[current];
  const signInHref = productAuthHref("/login", target);

  const signIn: ComponentProps<"a">["onClick"] = (event) => {
    // Plain clicks end this session first so /login starts clean; modified
    // clicks (new tab, copy link) keep the browser's default behaviour.
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    if (leaving) return;
    setLeaving(true);
    void signOutAndNavigate(signInHref);
  };

  function dismiss() {
    setDismissed(true);
    // Drop the query so a refresh does not bring the notice back, and hand
    // focus to the workspace instead of letting it fall to <body>.
    router.replace("/dashboard", { scroll: false });
    document.getElementById("workspace-content")?.focus();
  }

  return (
    <section
      className={styles.root}
      aria-labelledby="product-unavailable-title"
    >
      <Card className={styles.card}>
        <span className={styles.icon} aria-hidden="true">
          <ArrowLeftRight size={18} />
        </span>
        <div className={styles.body}>
          <h2 id="product-unavailable-title" className={styles.title}>
            That page is part of {targetMeta.name}
          </h2>
          <p className={styles.text}>
            You are signed in to {currentMeta.name}, so {targetMeta.label} pages
            are not available in this session. Sign in to {targetMeta.name} to
            open it. This signs you out of {currentMeta.label}.
          </p>
          <div className={styles.actions}>
            <a
              href={signInHref}
              className={styles.signIn}
              onClick={signIn}
              aria-disabled={leaving || undefined}
            >
              {leaving ? "Signing out…" : `Sign in to ${targetMeta.name}`}
            </a>
          </div>
        </div>
        <button
          type="button"
          className={styles.close}
          onClick={dismiss}
          aria-label="Dismiss notice"
        >
          <X size={16} aria-hidden="true" />
        </button>
      </Card>
    </section>
  );
}
