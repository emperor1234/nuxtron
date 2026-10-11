import type { Metadata, Route } from "next";
import type { ReactNode } from "react";
import Link from "next/link";
import {
  ArrowRight,
  KeyRound,
  Languages,
  Radar,
  ScrollText,
  ShieldCheck,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { productAuthHref } from "@/app/lib/product-line";
import { AnimatedIcon } from "../_components/sections/animated-icon";
import styles from "./tools.module.css";

export const metadata: Metadata = {
  title: "Free tools | Nuxtron",
  description:
    "Free local tools for AI crawlers, agent permissions, MCP configuration, and audit workflows from Nuxtron.",
  alternates: { canonical: "/tools" },
};

type Tool = {
  id: string;
  name: string;
  body: string;
  icon: ReactNode;
  /** Present only for tools that work today. */
  href?: string;
};

const TOOLS: readonly Tool[] = [
  {
    id: "ai-crawler-checker",
    name: "AI crawler checker",
    body: "Paste a robots.txt file to see how common AI search and assistant crawlers match its rules. Nothing is uploaded.",
    icon: <Radar size={20} strokeWidth={1.6} />,
    href: "/tools/ai-crawler-checker",
  },
  {
    id: "agent-permission-matrix",
    name: "Agent permission matrix",
    body: "Map an AI agent's data scope and actions to least-privilege access and explicit approval points.",
    icon: <ShieldCheck size={20} strokeWidth={1.6} />,
    href: "/tools/agent-permission-matrix",
  },
  {
    id: "mcp-security-scanner",
    name: "MCP security scanner",
    body: "Review a pasted MCP configuration for risky commands, broad access, insecure endpoints, and embedded secrets.",
    icon: <KeyRound size={20} strokeWidth={1.6} />,
    href: "/tools/mcp-security-scanner",
  },
  {
    id: "agent-audit-log-simulator",
    name: "Agent audit-log simulator",
    body: "Simulate a proposed, approved, denied, or completed agent action and inspect its illustrative audit trail.",
    icon: <ScrollText size={20} strokeWidth={1.6} />,
    href: "/tools/agent-audit-log-simulator",
  },
  {
    id: "translation-studio",
    name: "Translation Studio",
    body: "Translate and localize marketing copy while keeping your brand terms intact.",
    icon: <Languages size={20} strokeWidth={1.6} />,
    href: "/tools/translation-studio",
  },
];

export default function FreeToolsPage() {
  return (
    <div className={styles.page}>
      <header className={styles.hero}>
        <p className={styles.eyebrow}>Free tools</p>
        <h1 className={styles.title}>
          Useful on day one.
          <span className={styles.accent}>
            {" "}
            No account needed for these checks.
          </span>
        </h1>
        <p className={styles.intro}>
          The crawler, permission, MCP and audit tools run locally without an
          account. Translation Studio is a connected workspace tool and may
          require sign-in and provider setup.
        </p>
      </header>

      <ul className={styles.grid}>
        {TOOLS.map((tool) => (
          <li
            key={tool.id}
            id={tool.id}
            className={styles.card}
            data-icon-host
            data-live={Boolean(tool.href)}
          >
            <div className={styles.cardTop}>
              <AnimatedIcon glyph={tool.icon} />
              <span className={styles.badge} data-live={Boolean(tool.href)}>
                {tool.href ? "Available now" : "Coming soon"}
              </span>
            </div>
            <h2 className={styles.name}>{tool.name}</h2>
            <p className={styles.body}>{tool.body}</p>
            {tool.href ? (
              <Link href={tool.href as Route} className={styles.open}>
                Open the tool <ArrowRight size={15} aria-hidden="true" />
              </Link>
            ) : null}
          </li>
        ))}
      </ul>

      <section className={styles.cta} aria-labelledby="tools-cta">
        <h2 id="tools-cta">Want this running every day?</h2>
        <p>
          Nuxtron SEO tracks AI visibility, rankings and site health
          continuously.
        </p>
        <Button asChild size="lg">
          <Link href={productAuthHref("/register", "seo") as Route}>
            Start with Nuxtron SEO <ArrowRight data-icon="inline-end" />
          </Link>
        </Button>
      </section>
    </div>
  );
}
