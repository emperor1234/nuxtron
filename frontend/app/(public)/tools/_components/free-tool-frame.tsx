import type { ReactNode } from "react";
import Link from "next/link";
import { ArrowLeft, ShieldCheck } from "lucide-react";
import styles from "../tools.module.css";

type FreeToolFrameProps = {
  eyebrow?: string;
  title: string;
  description: string;
  children: ReactNode;
};

export function FreeToolFrame({
  eyebrow = "Nuxtron free tool",
  title,
  description,
  children,
}: FreeToolFrameProps) {
  return (
    <main className={styles.toolPage}>
      <Link href="/tools" className={styles.backLink}>
        <ArrowLeft size={16} aria-hidden="true" />
        All free tools
      </Link>
      <header className={styles.toolHeader}>
        <p className={styles.eyebrow}>{eyebrow}</p>
        <h1 className={styles.title}>{title}</h1>
        <p className={styles.intro}>{description}</p>
        <p className={styles.localNote}>
          <ShieldCheck size={16} aria-hidden="true" />
          Runs in your browser · no account or API key required
        </p>
      </header>
      <section className={styles.toolPanel} aria-label={`${title} tool`}>
        {children}
      </section>
    </main>
  );
}
