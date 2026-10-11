import styles from "./section-head.module.css";

/** The eyebrow / title / intro block every homepage section opens with. */
export function SectionHead({
  id,
  eyebrow,
  title,
  intro,
  align = "start",
  tone = "light",
}: {
  /** Id for the heading, referenced by the section's aria-labelledby. */
  id: string;
  eyebrow: string;
  title: string;
  intro?: string;
  align?: "start" | "center";
  tone?: "light" | "ink";
}) {
  return (
    <header className={styles.head} data-align={align} data-tone={tone}>
      <p className={styles.eyebrow}>{eyebrow}</p>
      <h2 id={id} className={styles.title}>
        {title}
      </h2>
      {intro ? <p className={styles.intro}>{intro}</p> : null}
    </header>
  );
}
