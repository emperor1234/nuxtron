import Image from "next/image";
import { getProviderMark } from "@/app/lib/provider-marks";
import styles from "./provider-logo.module.css";

type ProviderLogoProps = {
  label: string;
  size?: number;
  /** Use when a surrounding chart/list already provides an accessible name. */
  decorative?: boolean;
  className?: string;
};

/** Shows an unaltered provider mark, retaining a text fallback for unknown labels. */
export function ProviderLogo({
  label,
  size = 20,
  decorative = false,
  className,
}: ProviderLogoProps) {
  const mark = getProviderMark(label);
  if (!mark) {
    return decorative ? null : <span className={className}>{label}</span>;
  }

  return (
    <Image
      src={mark.src}
      alt={decorative ? "" : label}
      title={decorative ? undefined : label}
      aria-hidden={decorative || undefined}
      width={size}
      height={size}
      unoptimized
      className={[styles.logo, className].filter(Boolean).join(" ")}
      style={{ width: size, height: size }}
      data-provider={mark.key}
    />
  );
}
