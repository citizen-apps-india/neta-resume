import type { MetadataRoute } from "next";
import { getEciCourts, getEciPeople, getEciRules, listPersons, type PersonSummary } from "@/lib/api";
import { ECI_TILE_LAYOUT } from "@/lib/eci-numbers";

const SITE = "https://neta-resume.app";

// Refresh hourly so new legislators (the ongoing rollout) enter the sitemap without a redeploy.
export const revalidate = 3600;

const ECI_SECTIONS = ["", "/timeline", "/entries", "/numbers", "/people", "/selections", "/objections", "/answers", "/rules", "/courts"];

/** ECI Files people, court cases and rule diffs; empty if the API is unreachable, so the sitemap still serves. */
async function eciDetailRoutes(now: Date): Promise<MetadataRoute.Sitemap> {
  const [people, courts, rules] = await Promise.all([
    getEciPeople().catch(() => []),
    getEciCourts().then((c) => c.cases).catch(() => []),
    getEciRules().then((r) => r.diffs).catch(() => []),
  ]);
  const paths = [
    ...people.map((p) => `/eci-files/people/${p.slug}`),
    ...courts.map((c) => `/eci-files/courts/${c.slug}`),
    ...rules.map((d) => `/eci-files/rules/${d.id}`),
  ];
  return paths.map((path) => ({ url: `${SITE}${path}`, lastModified: now, changeFrequency: "monthly", priority: 0.5 }));
}

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
    ...ECI_SECTIONS.map((path) => ({
      url: `${SITE}/eci-files${path}`, lastModified: now, changeFrequency: "weekly" as const, priority: path ? 0.6 : 0.8,
    })),
    ...Object.keys(ECI_TILE_LAYOUT).map((slug) => ({
      url: `${SITE}/eci-files/numbers/${slug}`, lastModified: now, changeFrequency: "weekly" as const, priority: 0.5,
    })),
  ];

  const eciRoutes = await eciDetailRoutes(now);

  let people: PersonSummary[] = [];
  try {
    people = (await listPersons({ limit: 6000 })).items;
  } catch {
    return [...staticRoutes, ...eciRoutes];
  }
  const personRoutes: MetadataRoute.Sitemap = people.map((p) => ({
    url: `${SITE}/person/${p.id}`,
    lastModified: now,
    changeFrequency: "monthly",
    priority: 0.6,
  }));
  return [...staticRoutes, ...eciRoutes, ...personRoutes];
}
