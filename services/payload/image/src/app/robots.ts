import type { MetadataRoute } from 'next'

import { getServerSideURL } from '@/utilities/getURL'

// StackBlaze: served at request time so the sitemap links use this deploy's
// URL (upstream writes public/robots.txt with next-sitemap at build time).
export const dynamic = 'force-dynamic'

export default function robots(): MetadataRoute.Robots {
  const url = getServerSideURL()

  return {
    rules: [{ userAgent: '*', disallow: '/admin/*' }],
    sitemap: [`${url}/pages-sitemap.xml`, `${url}/posts-sitemap.xml`],
  }
}
