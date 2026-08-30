import type { ReactNode, ButtonHTMLAttributes, InputHTMLAttributes, SelectHTMLAttributes } from 'react';
import styles from './kit.module.css';

/**
 * Dashboard UI kit — the shared primitives every (dashboard) page composes from
 * so color, typography, spacing, and elevation stay consistent. Backed by the
 * tokens in `tokens.css`. Prefer these over per-page inline styles.
 */

function cx(...values: Array<string | false | undefined>): string {
  return values.filter(Boolean).join(' ');
}

/** Vertical page container with the standard section gap. */
export function Page({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cx(styles.page, className)}>{children}</div>;
}

/** Standard page header: title, optional subtitle, right-aligned actions. */
export function PageHeader({
  title,
  subtitle,
  actions,
}: {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
}) {
  return (
    <header className={styles.header}>
      <div>
        <div className={styles.titleRow}>
          <h1 className={styles.title}>{title}</h1>
        </div>
        {subtitle ? <p className={styles.subtitle}>{subtitle}</p> : null}
      </div>
      {actions ? <div className={styles.headerActions}>{actions}</div> : null}
    </header>
  );
}

export function FieldSelect({
  label,
  id,
  children,
  className,
  ...rest
}: SelectHTMLAttributes<HTMLSelectElement> & { label?: string }) {
  return (
    <div className={styles.field}>
      {label ? (
        <label className={styles.fieldLabel} htmlFor={id}>
          {label}
        </label>
      ) : null}
      <select id={id} className={cx(styles.input, className)} {...rest}>
        {children}
      </select>
    </div>
  );
}

/** Surface container. `pad` adds the standard interior padding. */
export function Card({
  children,
  pad = true,
  className,
}: {
  children: ReactNode;
  pad?: boolean;
  className?: string;
}) {
  return <div className={cx(styles.card, pad && styles.cardPad, className)}>{children}</div>;
}

export function CardTitle({ children, sub }: { children: ReactNode; sub?: string }) {
  return (
    <div>
      <h2 className={styles.cardTitle}>{children}</h2>
      {sub ? <p className={styles.cardSub}>{sub}</p> : null}
    </div>
  );
}

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: 'primary' | 'ghost' | 'danger';
};

export function Button({ variant = 'ghost', className, type, ...rest }: ButtonProps) {
  const variantClass =
    variant === 'primary' ? styles.btnPrimary : variant === 'danger' ? styles.btnDanger : styles.btnGhost;
  return <button type={type ?? 'button'} className={cx(styles.btn, variantClass, className)} {...rest} />;
}

type BadgeTone = 'neutral' | 'success' | 'brand' | 'danger';

export function Badge({ children, tone = 'neutral' }: { children: ReactNode; tone?: BadgeTone }) {
  const toneClass =
    tone === 'success'
      ? styles.badgeSuccess
      : tone === 'brand'
        ? styles.badgeBrand
        : tone === 'danger'
          ? styles.badgeDanger
          : styles.badgeNeutral;
  return <span className={cx(styles.badge, toneClass)}>{children}</span>;
}

/** Grid of key metrics. */
export function StatGrid({ children }: { children: ReactNode }) {
  return <div className={styles.statGrid}>{children}</div>;
}

export function Stat({ label, value, hint }: { label: string; value: ReactNode; hint?: string }) {
  return (
    <div className={styles.stat}>
      <span className={styles.statLabel}>{label}</span>
      <span className={styles.statValue}>{value}</span>
      {hint ? <span className={styles.statHint}>{hint}</span> : null}
    </div>
  );
}

/** Horizontally scrollable table wrapper for consistent overflow behavior. */
export function TableWrap({ children }: { children: ReactNode }) {
  return <div className={styles.tableWrap}>{children}</div>;
}

export const tableClass = styles.table;

type InputProps = InputHTMLAttributes<HTMLInputElement> & { label?: string };

export function Field({ label, className, id, ...rest }: InputProps) {
  return (
    <div className={styles.field}>
      {label ? (
        <label className={styles.fieldLabel} htmlFor={id}>
          {label}
        </label>
      ) : null}
      <input id={id} className={cx(styles.input, className)} {...rest} />
    </div>
  );
}
