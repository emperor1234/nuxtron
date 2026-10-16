"use client";

import Link from "next/link";
import type { Route } from "next";
import { useId, useState } from "react";
import type {
  ButtonHTMLAttributes,
  InputHTMLAttributes,
  ReactNode,
  SelectHTMLAttributes,
  TextareaHTMLAttributes,
} from "react";
import * as Dialog from "@radix-ui/react-dialog";
import {
  AlertTriangle,
  ArrowDown,
  ArrowUp,
  ArrowUpDown,
  CheckCircle2,
  Info,
  Inbox,
  Search,
  X,
} from "lucide-react";
import styles from "./kit.module.css";

/**
 * Nuxtron dashboard UI kit. Every product page composes from these primitives
 * so color, type, spacing and states stay consistent. Values come from the
 * tokens in `tokens.css`; do not add page-local brand colors.
 */

function cx(...values: Array<string | false | null | undefined>): string {
  return values.filter(Boolean).join(" ");
}

/* ------------------------------------------------------------------ layout */

/** Vertical page container with the standard section gap. */
export function Page({
  children,
  className,
  width = "default",
}: {
  children: ReactNode;
  className?: string;
  width?: "default" | "wide" | "narrow";
}) {
  return (
    <div
      className={cx(
        styles.page,
        width === "wide" && styles.pageWide,
        width === "narrow" && styles.pageNarrow,
        className,
      )}
    >
      {children}
    </div>
  );
}

export type Crumb = { label: string; href?: Route };

export type TabItem = { id: string; label: string; count?: number; href?: Route };

/** Standard page header: breadcrumbs, title, status meta, description, actions, optional tabs. */
export function PageHeader({
  title,
  subtitle,
  actions,
  meta,
  crumbs,
  tabs,
}: {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
  meta?: ReactNode;
  crumbs?: Crumb[];
  tabs?: ReactNode;
}) {
  return (
    <div className={styles.headerWrap}>
      {crumbs?.length ? (
        <nav className={styles.crumbs} aria-label="Breadcrumb">
          {crumbs.map((crumb, index) => (
            <span key={`${crumb.label}-${index}`} className={styles.row} style={{ gap: 6 }}>
              {index > 0 ? <span className={styles.crumbSep} aria-hidden="true">/</span> : null}
              {crumb.href ? <Link href={crumb.href}>{crumb.label}</Link> : <span>{crumb.label}</span>}
            </span>
          ))}
        </nav>
      ) : null}
      <header className={styles.header}>
        <div className={styles.headerMain}>
          <div className={styles.titleRow}>
            <h1 className={styles.title}>{title}</h1>
            {meta}
          </div>
          {subtitle ? <p className={styles.subtitle}>{subtitle}</p> : null}
        </div>
        {actions ? <div className={styles.headerActions}>{actions}</div> : null}
      </header>
      {tabs}
    </div>
  );
}

/** Tab strip. Pass `href` on items for route-based tabs, or `value`/`onChange` for in-page tabs. */
export function Tabs({
  items,
  value,
  onChange,
  label = "Sections",
}: {
  items: TabItem[];
  value: string;
  onChange?: (id: string) => void;
  label?: string;
}) {
  return (
    <div className={styles.tabs} role="tablist" aria-label={label}>
      {items.map((item) => {
        const active = item.id === value;
        const body = (
          <>
            {item.label}
            {item.count !== undefined ? <span className={styles.tabCount}>{item.count}</span> : null}
          </>
        );
        if (item.href) {
          return (
            <Link
              key={item.id}
              href={item.href}
              role="tab"
              aria-selected={active}
              className={cx(styles.tab, active && styles.tabActive)}
            >
              {body}
            </Link>
          );
        }
        return (
          <button
            key={item.id}
            type="button"
            role="tab"
            aria-selected={active}
            className={cx(styles.tab, active && styles.tabActive)}
            onClick={() => onChange?.(item.id)}
          >
            {body}
          </button>
        );
      })}
    </div>
  );
}

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

export function CardTitle({
  children,
  sub,
  actions,
}: {
  children: ReactNode;
  sub?: string;
  actions?: ReactNode;
}) {
  return (
    <div className={styles.cardHead}>
      <div>
        <h2 className={styles.cardTitle}>{children}</h2>
        {sub ? <p className={styles.cardSub}>{sub}</p> : null}
      </div>
      {actions ? <div className={styles.cardActions}>{actions}</div> : null}
    </div>
  );
}

/** Titled group of content on a page. */
export function Section({
  title,
  description,
  actions,
  children,
}: {
  title: string;
  description?: string;
  actions?: ReactNode;
  children: ReactNode;
}) {
  const id = useId();
  return (
    <section className={styles.section} aria-labelledby={id}>
      <div className={styles.sectionHead}>
        <div>
          <h2 id={id} className={styles.sectionTitle}>{title}</h2>
          {description ? <p className={styles.sectionDesc}>{description}</p> : null}
        </div>
        {actions ? <div className={styles.cardActions}>{actions}</div> : null}
      </div>
      {children}
    </section>
  );
}

export function Grid({ cols = 2, children }: { cols?: 2 | 3 | 4; children: ReactNode }) {
  return <div className={cols === 4 ? styles.grid4 : cols === 3 ? styles.grid3 : styles.grid2}>{children}</div>;
}

/** Form/controls column beside a results column. */
export function Split({ children, aside = "left" }: { children: ReactNode; aside?: "left" | "right" }) {
  return <div className={cx(styles.split, aside === "right" && styles.splitWide)}>{children}</div>;
}

export function Stack({ children }: { children: ReactNode }) {
  return <div className={styles.stack}>{children}</div>;
}

export function Row({ children }: { children: ReactNode }) {
  return <div className={styles.row}>{children}</div>;
}

/* ----------------------------------------------------------------- actions */

type ButtonVariant = "primary" | "secondary" | "ghost" | "quiet" | "danger";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
  size?: "sm" | "md";
  loading?: boolean;
  icon?: ReactNode;
};

function buttonClass(variant: ButtonVariant, size: "sm" | "md", className?: string): string {
  return cx(
    styles.btn,
    variant === "primary" && styles.btnPrimary,
    variant === "secondary" && styles.btnSecondary,
    variant === "ghost" && styles.btnGhost,
    variant === "quiet" && styles.btnQuiet,
    variant === "danger" && styles.btnDanger,
    size === "sm" && styles.btnSm,
    className,
  );
}

export function Button({
  variant = "ghost",
  size = "md",
  loading = false,
  icon,
  className,
  type,
  disabled,
  children,
  ...rest
}: ButtonProps) {
  return (
    <button
      type={type ?? "button"}
      className={buttonClass(variant, size, className)}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...rest}
    >
      {loading ? <span className={styles.spinner} aria-hidden="true" /> : icon}
      {children}
    </button>
  );
}

export function ButtonLink({
  href,
  variant = "ghost",
  size = "md",
  icon,
  children,
  className,
}: {
  href: Route;
  variant?: ButtonVariant;
  size?: "sm" | "md";
  icon?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <Link href={href} className={buttonClass(variant, size, className)}>
      {icon}
      {children}
    </Link>
  );
}

export function IconButton({
  label,
  children,
  variant = "ghost",
  ...rest
}: Omit<ButtonProps, "size" | "loading" | "icon"> & { label: string }) {
  return (
    <button
      type="button"
      className={cx(buttonClass(variant, "sm"), styles.iconBtn)}
      aria-label={label}
      title={label}
      {...rest}
    >
      {children}
    </button>
  );
}

/* ------------------------------------------------------------------ status */

export type BadgeTone = "neutral" | "success" | "brand" | "danger" | "warning" | "info";

export function Badge({ children, tone = "neutral" }: { children: ReactNode; tone?: BadgeTone }) {
  return (
    <span
      className={cx(
        styles.badge,
        tone === "neutral" && styles.badgeNeutral,
        tone === "brand" && styles.badgeBrand,
        tone === "success" && styles.badgeSuccess,
        tone === "warning" && styles.badgeWarning,
        tone === "danger" && styles.badgeDanger,
        tone === "info" && styles.badgeInfo,
      )}
    >
      {children}
    </span>
  );
}

/** Maps a record status string onto a badge tone so lists read consistently. */
export function StatusBadge({ status }: { status: string | null | undefined }) {
  const value = (status ?? "unknown").toLowerCase();
  const tone: BadgeTone =
    ["active", "approved", "published", "connected", "completed", "complete", "live", "healthy", "success", "paid", "resolved", "won", "ok"].includes(value)
      ? "success"
      : ["pending", "scheduled", "queued", "draft", "processing", "running", "in_progress", "in review", "open", "warning", "trial"].includes(value)
        ? "warning"
        : ["failed", "rejected", "error", "expired", "cancelled", "canceled", "lost", "overdue", "blocked", "toxic", "unavailable"].includes(value)
          ? "danger"
          : "neutral";
  return <Badge tone={tone}>{status ? status.replace(/[_-]/g, " ") : "Unknown"}</Badge>;
}

export type DataStatusState = "live" | "preview" | "unavailable";

/**
 * Declares whether a data-driven surface is backed by live provider data.
 * Never use the success state for seeded, fallback, demo, or mock responses.
 */
export function DataStatus({ state, provider }: { state: DataStatusState; provider?: string }) {
  const providerName = provider?.trim();
  const label =
    state === "live"
      ? `Live data${providerName ? ` · ${providerName}` : ""}`
      : state === "preview"
        ? `Preview data${providerName ? ` — connect ${providerName} to activate` : ""}`
        : `Data unavailable${providerName ? ` · ${providerName}` : ""}`;
  const stateClass =
    state === "live"
      ? styles.dataStatusLive
      : state === "preview"
        ? styles.dataStatusPreview
        : styles.dataStatusUnavailable;

  return (
    <span className={cx(styles.dataStatus, stateClass)} role="status">
      <span className={styles.dataStatusDot} aria-hidden="true" />
      {label}
    </span>
  );
}

export function Callout({
  tone = "info",
  title,
  children,
}: {
  tone?: "info" | "warning" | "danger" | "success";
  title?: string;
  children?: ReactNode;
}) {
  const Icon = tone === "success" ? CheckCircle2 : tone === "info" ? Info : AlertTriangle;
  return (
    <div
      className={cx(
        styles.callout,
        tone === "info" && styles.calloutInfo,
        tone === "warning" && styles.calloutWarning,
        tone === "danger" && styles.calloutDanger,
        tone === "success" && styles.calloutSuccess,
      )}
      role={tone === "danger" ? "alert" : "status"}
    >
      <Icon size={18} aria-hidden="true" style={{ flex: "none", marginTop: 2 }} />
      <div className={styles.calloutBody}>
        {title ? <p className={styles.calloutTitle}>{title}</p> : null}
        {children}
      </div>
    </div>
  );
}

/* --------------------------------------------------------------------- KPI */

export function KpiGrid({ children }: { children: ReactNode }) {
  return <div className={styles.kpiGrid}>{children}</div>;
}

/** Back-compat alias used by older pages. */
export const StatGrid = KpiGrid;

export function Kpi({
  label,
  value,
  hint,
  delta,
}: {
  label: string;
  value: ReactNode;
  hint?: string;
  /** Signed change, e.g. +4.2. Omit when no comparison period exists. */
  delta?: number | null;
}) {
  return (
    <div className={styles.kpi}>
      <span className={styles.kpiLabel}>{label}</span>
      <span className={styles.kpiValue}>{value}</span>
      {typeof delta === "number" ? (
        <span className={cx(styles.kpiDelta, delta >= 0 ? styles.deltaUp : styles.deltaDown)}>
          {delta >= 0 ? "▲" : "▼"} {Math.abs(delta).toLocaleString(undefined, { maximumFractionDigits: 1 })}%
        </span>
      ) : null}
      {hint ? <span className={styles.kpiHint}>{hint}</span> : null}
    </div>
  );
}

export const Stat = Kpi;

/* ------------------------------------------------------------------- forms */

type FieldShell = { label?: string; hint?: string; error?: string };

function FieldFrame({
  id,
  label,
  hint,
  error,
  children,
}: FieldShell & { id: string; children: ReactNode }) {
  return (
    <div className={styles.field}>
      {label ? (
        <label className={styles.fieldLabel} htmlFor={id}>
          {label}
        </label>
      ) : null}
      {children}
      {error ? (
        <span className={styles.fieldError} id={`${id}-error`} role="alert">
          {error}
        </span>
      ) : hint ? (
        <span className={styles.fieldHint} id={`${id}-hint`}>
          {hint}
        </span>
      ) : null}
    </div>
  );
}

type InputProps = InputHTMLAttributes<HTMLInputElement> & FieldShell;

export function Field({ label, hint, error, className, id, ...rest }: InputProps) {
  const auto = useId();
  const fieldId = id ?? auto;
  return (
    <FieldFrame id={fieldId} label={label} hint={hint} error={error}>
      <input
        id={fieldId}
        className={cx(styles.input, error && styles.invalid, className)}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? `${fieldId}-error` : hint ? `${fieldId}-hint` : undefined}
        {...rest}
      />
    </FieldFrame>
  );
}

export function FieldSelect({
  label,
  hint,
  error,
  id,
  children,
  className,
  ...rest
}: SelectHTMLAttributes<HTMLSelectElement> & FieldShell) {
  const auto = useId();
  const fieldId = id ?? auto;
  return (
    <FieldFrame id={fieldId} label={label} hint={hint} error={error}>
      <select
        id={fieldId}
        className={cx(styles.select, error && styles.invalid, className)}
        aria-invalid={error ? true : undefined}
        {...rest}
      >
        {children}
      </select>
    </FieldFrame>
  );
}

export function FieldTextarea({
  label,
  hint,
  error,
  id,
  className,
  ...rest
}: TextareaHTMLAttributes<HTMLTextAreaElement> & FieldShell) {
  const auto = useId();
  const fieldId = id ?? auto;
  return (
    <FieldFrame id={fieldId} label={label} hint={hint} error={error}>
      <textarea
        id={fieldId}
        className={cx(styles.textarea, error && styles.invalid, className)}
        aria-invalid={error ? true : undefined}
        {...rest}
      />
    </FieldFrame>
  );
}

export function Checkbox({ label, ...rest }: InputHTMLAttributes<HTMLInputElement> & { label: string }) {
  return (
    <label className={styles.check}>
      <input type="checkbox" {...rest} />
      {label}
    </label>
  );
}

export function Switch({
  label,
  checked,
  onChange,
  disabled,
}: {
  label: string;
  checked: boolean;
  onChange: (next: boolean) => void;
  disabled?: boolean;
}) {
  return (
    <label className={styles.switch}>
      <input
        type="checkbox"
        role="switch"
        checked={checked}
        disabled={disabled}
        onChange={(event) => onChange(event.target.checked)}
      />
      <span className={styles.switchTrack} aria-hidden="true" />
      {label}
    </label>
  );
}

export function FormGrid({ children }: { children: ReactNode }) {
  return <div className={styles.formGrid}>{children}</div>;
}

export function FormActions({ children }: { children: ReactNode }) {
  return <div className={styles.formActions}>{children}</div>;
}

/* ----------------------------------------------------------------- toolbar */

export function Toolbar({ children }: { children: ReactNode }) {
  return <div className={styles.toolbar}>{children}</div>;
}

export function SearchField({
  value,
  onChange,
  placeholder = "Search",
  label = "Search",
}: {
  value: string;
  onChange: (next: string) => void;
  placeholder?: string;
  label?: string;
}) {
  return (
    <div className={cx(styles.searchBox, styles.toolbarGrow)}>
      <Search size={15} aria-hidden="true" />
      <input
        type="search"
        className={styles.input}
        value={value}
        placeholder={placeholder}
        aria-label={label}
        onChange={(event) => onChange(event.target.value)}
      />
    </div>
  );
}

/* ------------------------------------------------------------------- table */

export type Column<T> = {
  key: string;
  header: string;
  render: (row: T) => ReactNode;
  /** Returning a comparable value makes the column sortable. */
  sortValue?: (row: T) => string | number | null | undefined;
  numeric?: boolean;
  strong?: boolean;
};

/**
 * Sortable data table with an honest empty state. Pagination is client-side:
 * pass `pageSize` when a result set can be long.
 */
export function DataTable<T>({
  columns,
  rows,
  getKey,
  onRowClick,
  empty,
  caption,
  pageSize,
  dense,
}: {
  columns: Column<T>[];
  rows: T[];
  getKey: (row: T, index: number) => string | number;
  onRowClick?: (row: T) => void;
  empty?: ReactNode;
  caption: string;
  pageSize?: number;
  dense?: boolean;
}) {
  const [sort, setSort] = useState<{ key: string; dir: 1 | -1 } | null>(null);
  const [page, setPage] = useState(0);

  const column = sort ? columns.find((item) => item.key === sort.key) : undefined;
  const sorted =
    sort && column?.sortValue
      ? [...rows].sort((a, b) => {
          const left = column.sortValue!(a);
          const right = column.sortValue!(b);
          const leftMissing = left === null || left === undefined;
          const rightMissing = right === null || right === undefined;
          if (leftMissing && rightMissing) return 0;
          if (leftMissing) return 1;
          if (rightMissing) return -1;
          if (typeof left === "number" && typeof right === "number") return (left - right) * sort.dir;
          return String(left).localeCompare(String(right), undefined, { numeric: true, sensitivity: "base" }) * sort.dir;
        })
      : rows;

  const pages = pageSize ? Math.max(1, Math.ceil(sorted.length / pageSize)) : 1;
  const safePage = Math.min(page, pages - 1);
  const visible = pageSize ? sorted.slice(safePage * pageSize, (safePage + 1) * pageSize) : sorted;

  if (rows.length === 0) return <>{empty ?? <EmptyState title="Nothing here yet" />}</>;

  return (
    <div className={cx(styles.card, styles.tableCard)}>
      <div className={styles.tableWrap}>
        <table className={cx(styles.table, dense && styles.dense)}>
          <caption className={styles.srOnly}>{caption}</caption>
          <thead>
            <tr>
              {columns.map((item) => {
                const active = sort?.key === item.key;
                return (
                  <th
                    key={item.key}
                    scope="col"
                    className={item.numeric ? styles.numeric : undefined}
                    aria-sort={active ? (sort!.dir === 1 ? "ascending" : "descending") : undefined}
                  >
                    {item.sortValue ? (
                      <button
                        type="button"
                        className={styles.sortBtn}
                        onClick={() => {
                          setSort(active && sort!.dir === -1 ? null : { key: item.key, dir: active ? -1 : 1 });
                          setPage(0);
                        }}
                      >
                        {item.header}
                        {active ? (
                          sort!.dir === 1 ? <ArrowUp size={12} aria-hidden="true" /> : <ArrowDown size={12} aria-hidden="true" />
                        ) : (
                          <ArrowUpDown size={12} aria-hidden="true" />
                        )}
                      </button>
                    ) : (
                      item.header
                    )}
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {visible.map((row, index) => (
              <tr
                key={getKey(row, index)}
                className={onRowClick ? styles.rowClickable : undefined}
                onClick={onRowClick ? () => onRowClick(row) : undefined}
              >
                {columns.map((item) => (
                  <td
                    key={item.key}
                    className={cx(item.numeric && styles.numeric, item.strong && styles.cellStrong)}
                  >
                    {item.render(row)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {pageSize && sorted.length > pageSize ? (
        <div className={styles.tableFoot}>
          <span>
            {safePage * pageSize + 1}–{Math.min((safePage + 1) * pageSize, sorted.length)} of {sorted.length}
          </span>
          <span className={styles.row}>
            <Button size="sm" disabled={safePage === 0} onClick={() => setPage(safePage - 1)}>
              Previous
            </Button>
            <Button size="sm" disabled={safePage >= pages - 1} onClick={() => setPage(safePage + 1)}>
              Next
            </Button>
          </span>
        </div>
      ) : null}
    </div>
  );
}

/** Horizontally scrollable table wrapper for hand-built tables. */
export function TableWrap({ children }: { children: ReactNode }) {
  return <div className={styles.tableWrap}>{children}</div>;
}

export const tableClass = styles.table;

/* ------------------------------------------------------------------ states */

export function EmptyState({
  title,
  description,
  action,
  icon,
}: {
  title: string;
  description?: string;
  action?: ReactNode;
  icon?: ReactNode;
}) {
  return (
    <div className={styles.state}>
      <span className={styles.stateIcon}>{icon ?? <Inbox size={22} aria-hidden="true" />}</span>
      <h3 className={styles.stateTitle}>{title}</h3>
      {description ? <p className={styles.stateText}>{description}</p> : null}
      {action}
    </div>
  );
}

/**
 * Failure state. A 501/"not implemented" response is shown as a notice (the
 * capability is not configured) rather than as a crash.
 */
export function ErrorState({
  error,
  onRetry,
  title,
}: {
  error: unknown;
  onRetry?: () => void;
  title?: string;
}) {
  const status = (error as { status?: number } | null)?.status;
  const message = error instanceof Error ? error.message : "Something went wrong.";
  const notConfigured = status === 501 || status === 503;
  return (
    <div className={cx(styles.state, notConfigured ? styles.stateNotice : styles.stateError)} role="alert">
      <span className={styles.stateIcon}>
        <AlertTriangle size={22} aria-hidden="true" />
      </span>
      <h3 className={styles.stateTitle}>
        {title ?? (notConfigured ? "This capability isn't available yet" : "We couldn't load this")}
      </h3>
      <p className={styles.stateText}>{message}</p>
      {onRetry && !notConfigured ? (
        <Button variant="secondary" onClick={onRetry}>
          Try again
        </Button>
      ) : null}
    </div>
  );
}

export function Skeleton({ height = 16, width = "100%" }: { height?: number; width?: number | string }) {
  return <div className={styles.skel} style={{ height, width }} aria-hidden="true" />;
}

export function LoadingState({ label = "Loading" }: { label?: string }) {
  return (
    <div className={styles.skelStack} role="status" aria-live="polite">
      <span className={styles.srOnly}>{label}…</span>
      <Skeleton height={72} />
      <Skeleton height={220} />
    </div>
  );
}

/* ---------------------------------------------------------------- overlays */

function OverlayHead({ title, description }: { title: string; description?: string }) {
  return (
    <div className={styles.overlayHead}>
      <div>
        <Dialog.Title className={styles.overlayTitle}>{title}</Dialog.Title>
        {description ? (
          <Dialog.Description className={styles.overlayDesc}>{description}</Dialog.Description>
        ) : (
          <Dialog.Description className={styles.srOnly}>{title}</Dialog.Description>
        )}
      </div>
      <Dialog.Close asChild>
        <IconButton label="Close" variant="quiet">
          <X size={16} aria-hidden="true" />
        </IconButton>
      </Dialog.Close>
    </div>
  );
}

export function Modal({
  open,
  onOpenChange,
  title,
  description,
  children,
  footer,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: string;
  children: ReactNode;
  footer?: ReactNode;
}) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className={styles.overlay} />
        <Dialog.Content className={cx("nxScope", styles.modal)}>
          <OverlayHead title={title} description={description} />
          {children}
          {footer ? <div className={styles.overlayFoot}>{footer}</div> : null}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

export function Drawer({
  open,
  onOpenChange,
  title,
  description,
  children,
  footer,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: string;
  children: ReactNode;
  footer?: ReactNode;
}) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className={styles.overlay} />
        <Dialog.Content className={cx("nxScope", styles.drawer)}>
          <OverlayHead title={title} description={description} />
          {children}
          {footer ? <div className={styles.overlayFoot}>{footer}</div> : null}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

/* --------------------------------------------------------------------- viz */

function scoreTone(value: number): string {
  if (value >= 70) return "var(--nx-success)";
  if (value >= 45) return "var(--nx-warning)";
  return "var(--nx-danger)";
}

/** Circular 0–100 score. Colour reflects the band; the number is always shown. */
export function ScoreRing({ value, size = 72, label }: { value: number; size?: number; label?: string }) {
  const clamped = Math.max(0, Math.min(100, Number.isFinite(value) ? value : 0));
  const stroke = Math.max(6, Math.round(size / 10));
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  return (
    <span
      className={styles.ring}
      style={{ width: size, height: size }}
      role="img"
      aria-label={`${label ? `${label}: ` : ""}${Math.round(clamped)} out of 100`}
    >
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} aria-hidden="true">
        <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="var(--nx-border-soft)" strokeWidth={stroke} />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={scoreTone(clamped)}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={circumference * (1 - clamped / 100)}
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
        />
      </svg>
      <span className={styles.ringValue} style={{ fontSize: Math.round(size / 3.2) }}>
        {Math.round(clamped)}
      </span>
    </span>
  );
}

/** Horizontal bar for a single measure. `max` defaults to 100 (percent-like scores). */
export function Meter({
  label,
  value,
  max = 100,
  format,
  tone = "auto",
}: {
  label: string;
  value: number;
  max?: number;
  format?: (value: number) => string;
  tone?: "auto" | "brand";
}) {
  const ratio = max > 0 ? Math.max(0, Math.min(1, value / max)) : 0;
  const band = ratio * 100;
  const fillClass =
    tone === "brand" ? undefined : band >= 70 ? styles.meterGood : band >= 45 ? styles.meterWarn : styles.meterBad;
  return (
    <div className={styles.meter}>
      <div className={styles.meterRow}>
        <span className={styles.meterLabel}>{label}</span>
        <span className={styles.meterValue}>{format ? format(value) : value.toLocaleString()}</span>
      </div>
      <div
        className={styles.meterTrack}
        role="meter"
        aria-label={label}
        aria-valuemin={0}
        aria-valuemax={max}
        aria-valuenow={value}
      >
        <div className={cx(styles.meterFill, fillClass)} style={{ width: `${ratio * 100}%` }} />
      </div>
    </div>
  );
}

export function KeyValue({ items }: { items: Array<{ label: string; value: ReactNode }> }) {
  return (
    <dl className={styles.kv}>
      {items.map((item) => (
        <div key={item.label} style={{ display: "contents" }}>
          <dt>{item.label}</dt>
          <dd>{item.value}</dd>
        </div>
      ))}
    </dl>
  );
}

export function BulletList({ items }: { items: ReactNode[] }) {
  return (
    <ul className={styles.list}>
      {items.map((item, index) => (
        <li key={index} className={styles.listItem}>
          <span className={styles.listDot} aria-hidden="true" />
          <span>{item}</span>
        </li>
      ))}
    </ul>
  );
}

export function Chip({ children }: { children: ReactNode }) {
  return <span className={styles.chip}>{children}</span>;
}

export function Prose({ children }: { children: ReactNode }) {
  return <div className={styles.prose}>{children}</div>;
}

/** Confirmation for destructive actions. The confirm button runs `onConfirm` and the dialog stays until it settles. */
export function ConfirmModal({
  open,
  onOpenChange,
  title,
  description,
  confirmLabel = "Delete",
  onConfirm,
  pending,
  error,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: string;
  confirmLabel?: string;
  onConfirm: () => void;
  pending?: boolean;
  error?: string | null;
}) {
  return (
    <Modal
      open={open}
      onOpenChange={onOpenChange}
      title={title}
      description={description}
      footer={
        <>
          <Button onClick={() => onOpenChange(false)} disabled={pending}>
            Cancel
          </Button>
          <Button variant="danger" onClick={onConfirm} loading={pending}>
            {confirmLabel}
          </Button>
        </>
      }
    >
      {error ? <Callout tone="danger">{error}</Callout> : null}
    </Modal>
  );
}
