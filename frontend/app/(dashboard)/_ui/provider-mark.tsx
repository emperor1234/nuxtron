import Image from "next/image";
import { getProviderMark } from "@/app/lib/provider-marks";

type ProviderMarkProps = {
  name: string;
  size?: number;
  /** Use when adjacent visible text already identifies the provider. */
  decorative?: boolean;
  className?: string;
};

/** An unchanged third-party mark for factual dashboard identification only. */
export function ProviderMark({
  name,
  size = 18,
  decorative = false,
  className,
}: ProviderMarkProps) {
  const mark = getProviderMark(name);
  if (!mark) return null;

  return (
    <Image
      src={mark.src}
      alt={decorative ? "" : name}
      aria-hidden={decorative || undefined}
      title={name}
      width={size}
      height={size}
      unoptimized
      className={
        className ?? "inline-block shrink-0 align-middle object-contain"
      }
      style={{ width: size, height: size }}
      data-provider={mark.key}
    />
  );
}
