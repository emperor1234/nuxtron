import Link from "next/link";
import { ArrowUpRight, Coins, Images, ReceiptText, Wallet } from "lucide-react";
import styles from "./social-studio-header.module.css";

/**
 * Social Studio page header in the shared dashboard style: title,
 * plain-language description and labelled account figures. Replaces the old
 * dark "control tower" panel, whose ink text sat on a near-black gradient.
 */
export function SocialStudioHeader({
  credits,
  pendingTopups,
  walletUsd,
  generatedCount,
  error,
}: {
  credits: number | null;
  pendingTopups: number | null;
  walletUsd: number | null;
  generatedCount: number;
  error?: string;
}) {
  const figures = [
    { label: "Credits available", value: credits?.toLocaleString("en-US") ?? "—", Icon: Coins },
    { label: "Top-ups pending", value: pendingTopups?.toLocaleString("en-US") ?? "—", Icon: ReceiptText },
    { label: "Wallet balance", value: walletUsd === null ? "—" : `$${walletUsd.toFixed(2)}`, Icon: Wallet },
    { label: "Created this session", value: generatedCount.toLocaleString("en-US"), Icon: Images },
  ];
  return (
    <header className={styles.header}>
      <div className={styles.titleRow}>
        <div>
          <h1 className={styles.title}>Social Studio</h1>
          <p className={styles.subtitle}>
            Create campaign content, connect your channels and publish across social accounts from one place.
          </p>
        </div>
        <Link href="/studio/content-hub" className={styles.hubLink}>
          Open the AI content hub <ArrowUpRight size={14} aria-hidden="true" />
        </Link>
      </div>
      {error ? (
        <p role="status" className={styles.error}>
          {error} — some features may be unavailable.
        </p>
      ) : null}
      <dl className={styles.figures}>
        {figures.map(({ label, value, Icon }) => (
          <div key={label} className={styles.figure}>
            <dt>
              <Icon size={14} aria-hidden="true" />
              {label}
            </dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
    </header>
  );
}
