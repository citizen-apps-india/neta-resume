import type { MetadataRoute } from "next";
import { connection } from "next/server";
import { getEciCourts, getEciPeople, getEciRules, listPersons, type PersonSummary } from "@/lib/api";
import { ECI_TILE_LAYOUT } from "@/lib/eci-numbers";

const SITE = "https://neta-resume.app";


const ECI_SECTIONS = ["", "/timeline", "/entries", "/numbers", "/people", "/selections", "/objections", "/answers", "/rules", "/courts"];

/** ECI Files people, court cases and rule diffs. */
async function eciDetailRoutes(now: Date): Promise<MetadataRoute.Sitemap> {
  const [people, courts, rules] = await Promise.all([
    getEciPeople(),
    getEciCourts().then((c) => c.cases),
    getEciRules().then((r) => r.diffs),
  ]);
  const paths = [
    ...people.map((p) => `/eci-files/people/${p.slug}`),
    ...courts.map((c) => `/eci-files/courts/${c.slug}`),
    ...rules.map((d) => `/eci-files/rules/${d.id}`),
  ];
  return paths.map((path) => ({ url: `${SITE}${path}`, lastModified: now, changeFrequency: "monthly", priority: 0.5 }));
}

/** The API returns at most this many rows per page. */
const PERSONS_PAGE = 200;

/** Every legislator, read page by page. */
async function allPersons(): Promise<PersonSummary[]> {
  const first = await listPersons({ limit: PERSONS_PAGE, offset: 0 });
  const people = [...first.items];
  while (people.length < first.total) {
    const next = await listPersons({ limit: PERSONS_PAGE, offset: people.length });
    if (next.items.length === 0) throw new Error(`sitemap: /persons stopped at ${people.length} of ${first.total}`);
    people.push(...next.items);
  }
  return people;
}

/** Served at /sitemap.xml: the section pages plus one entry per legislator, so Google can discover and
 *  index every profile. Built per request from the day-long API cache (never at build time, when the API
 *  may be unreachable). If the API fails and nothing is cached, this answers 500 rather than a shorter
 *  sitemap. */
export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  await connection();
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

  const [eciRoutes, people] = await Promise.all([eciDetailRoutes(now), allPersons()]);
  const personRoutes: MetadataRoute.Sitemap = people.map((p) => ({
    url: `${SITE}/person/${p.id}`,
    lastModified: now,
    changeFrequency: "monthly",
    priority: 0.6,
  }));
  return [...staticRoutes, ...eciRoutes, ...personRoutes];
}
