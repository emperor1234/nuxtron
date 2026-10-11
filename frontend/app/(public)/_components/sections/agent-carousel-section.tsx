import type { Route } from "next";
import Link from "next/link";
import { ArrowRight, Bot } from "lucide-react";
import { AnimatedIcon } from "./animated-icon";
import type { AgentCard, AgentContent } from "../../_content/types";
import { Reveal } from "../reveal";
import { Carousel } from "./carousel";
import styles from "./agent-carousel-section.module.css";

const HEADING_ID = "home-agents-title";

/**
 * Carousel of the AI agents that ship in the product. Copy comes entirely
 * from `content`; this component adds no capabilities of its own.
 */
export function AgentCarouselSection({ content }: { content: AgentContent }) {
  if (content.agents.length === 0) return null;

  return (
    <section className={styles.section} aria-labelledby={HEADING_ID}>
      <Reveal className={styles.heading}>
        <p className={styles.eyebrow}>
          <span aria-hidden="true" />
          {content.eyebrow}
        </p>
        <h2 id={HEADING_ID}>{content.title}</h2>
        <p className={styles.intro}>{content.intro}</p>
      </Reveal>
      <Reveal delay={0.06}>
        <Carousel label={content.title}>
          {content.agents.map((agent) => (
            <AgentSlide key={agent.id} agent={agent} />
          ))}
        </Carousel>
      </Reveal>
    </section>
  );
}

function AgentSlide({ agent }: { agent: AgentCard }) {
  return (
    <article className={styles.card} data-icon-host>
      <span className={styles.iconTile}>
        <AnimatedIcon glyph={<Bot size={22} strokeWidth={1.6} />} />
      </span>
      <div className={styles.titles}>
        <h3>{agent.name}</h3>
        <p className={styles.role}>{agent.role}</p>
      </div>
      <p className={styles.body}>{agent.body}</p>
      {agent.actions.length > 0 ? (
        <ul className={styles.actions} aria-label={`What ${agent.name} does`}>
          {agent.actions.map((action) => (
            <li key={action}>{action}</li>
          ))}
        </ul>
      ) : null}
      <AgentLink agent={agent} />
    </article>
  );
}

/** The card's single link; its ::after stretches over the card as the hit area. */
function AgentLink({ agent }: { agent: AgentCard }) {
  const { href, label } = agent.link;
  const contents = (
    <>
      {label}
      <span className="sr-only">: {agent.name}</span>
      <ArrowRight size={15} strokeWidth={1.8} aria-hidden="true" />
    </>
  );
  if (/^https:\/\//.test(href)) {
    return (
      <a className={styles.link} href={href} target="_blank" rel="noopener noreferrer">
        {contents}
        <span className="sr-only"> (opens in a new tab)</span>
      </a>
    );
  }
  return (
    <Link className={styles.link} href={href as Route}>
      {contents}
    </Link>
  );
}
