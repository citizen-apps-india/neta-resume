import type { EciEntry, EciFilesLane } from "@/types/eci-files";

// Shared by the server profile page (section nav counts) and the client `PersonEntrySections`, which is
// why it lives outside that "use client" file.
export const SECTION_LANES: { id: string; heading: string; intro: (name: string) => string; lanes: EciFilesLane[] }[] = [
  {
    id: "decisions", heading: "Decisions & objections", lanes: ["commission", "inside"],
    intro: (name) => `What the Commission did while ${name} served, and objections recorded inside it that name ${name}.`,
  },
  {
    id: "mentions", heading: "Mentions", lanes: ["courts", "claims"],
    intro: (name) => `Court proceedings and claims by others that name ${name}.`,
  },
  {
    id: "responses", heading: "Responses", lanes: ["responses"],
    intro: (name) => `Answers on the record from ${name}, the Commission or the government.`,
  },
];

/** Counts for the section nav — computed the same way `PersonEntrySections` splits, so the nav's numbers
 *  always match what actually renders. */
export function personEntrySectionCounts(entries: EciEntry[]): { id: string; label: string; count: number }[] {
  return SECTION_LANES.map((s) => ({
    id: s.id,
    label: s.heading,
    count: entries.filter((e) => s.lanes.includes(e.lane)).length,
  }));
}
