'use client';

import Image from 'next/image';

type BrandLogoProps = {
  width?: number;
  height?: number;
  priority?: boolean;
  className?: string;
};

const LOGO_SRC = '/brand/nuxtron-wordmark-dark.svg';

export default function BrandLogo({
  width = 220,
  height = 48,
  priority = false,
  className,
}: Readonly<BrandLogoProps>) {
  return (
    <Image
      src={LOGO_SRC}
      alt="Nuxtron"
      width={width}
      height={height}
      priority={priority}
      className={className}
      unoptimized
    />
  );
}
