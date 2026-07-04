import type { MetadataRoute } from "next";
import { listPersons, type PersonSummary } from "@/lib/api";

const SITE = "https://neta-resume.app";

// Refresh hourly so new legislators (the ongoing rollout) enter the sitemap without a redeploy.
export const revalidate = 3600;

/** Served at /sitemap.xml — the section pages plus one entry per legislator, so Google can discover and
 *  index every profile (the key to name-searchability). Falls back to just the section pages if the API
 *  is briefly unreachable, rather than 500-ing the whole sitemap. */
export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const now = new Date();
  const staticRoutes: MetadataRoute.Sitemap = [
    { url: `${SITE}/`, lastModified: now, changeFrequency: "daily", priority: 1 },
    { url: `${SITE}/lok-sabha`, lastModified: now, changeFrequency: "weekly", priority: 0.9 },
    { url: `${SITE}/rajya-sabha`, lastModified: now, changeFrequency: "weekly", priority: 0.9 },
    { url: `${SITE}/state-level`, lastModified: now, changeFrequency: "weekly", priority: 0.9 },
    { url: `${SITE}/directory`, lastModified: now, changeFrequency: "weekly", priority: 0.8 },
    { url: `${SITE}/municipal`, lastModified: now, changeFrequency: "weekly", priority: 0.7 },
    { url: `${SITE}/elections`, lastModified: now, changeFrequency: "monthly", priority: 0.6 },
  ];

  let people: PersonSummary[] = [];
  try {
    people = (await listPersons({ limit: 6000 })).items;
  } catch {
    return staticRoutes;
  }
  const personRoutes: MetadataRoute.Sitemap = people.map((p) => ({
    url: `${SITE}/person/${p.id}`,
    lastModified: now,
    changeFrequency: "monthly",
    priority: 0.6,
  }));
  return [...staticRoutes, ...personRoutes];
}
