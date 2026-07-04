import type { MetadataRoute } from "next";

const SITE = "https://neta-resume.app";

/** Served at /robots.txt — allow full crawling and point crawlers at the sitemap. */
export default function robots(): MetadataRoute.Robots {
  return {
    rules: { userAgent: "*", allow: "/" },
    sitemap: `${SITE}/sitemap.xml`,
    host: SITE,
  };
}
