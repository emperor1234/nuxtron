'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

/** Legacy route — canonical Local SEO UI lives at /seo/local */
export default function LocalSeoLegacyRedirectPage() {
  const router = useRouter();
  useEffect(() => {
    router.replace('/seo/local');
  }, [router]);
  return null;
}
