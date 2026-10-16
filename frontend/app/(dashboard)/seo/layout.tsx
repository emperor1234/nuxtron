import type { ReactNode } from "react";

export default function SeoLayout({ children }: Readonly<{ children: ReactNode }>) {
  return <div className="seo-product-surface">{children}</div>;
}
