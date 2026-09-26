"use client";

import { useState } from "react";
import type { EciEntry } from "@/types/eci-files";
import { SECTION_LANES } from "@/lib/eci-person-sections";
import { EntryCard } from "@/components/eci-files/EntryCard";

const PAGE = 8;

function EntrySectionList({ id, heading, intro, entries }: { id: string; heading: string; intro: string; entries: EciEntry[] }) {
  const [expanded, setExpanded] = useState(false);
  if (entries.length === 0) return null;
  const shown = expanded ? entries : entries.slice(0, PAGE);

  return (
    <section id={id} style={{ marginBottom: 30 }}>
      <h2 className="serif" style={{ fontSize: 20, fontWeight: 600, margin: "0 0 4px" }}>
        {heading} <span className="mono" style={{ fontSize: 13, color: "var(--faint)", fontWeight: 400 }}>{entries.length}</span>
      </h2>
      <p style={{ fontSize: 12.5, color: "var(--muted)", margin: "0 0 12px", maxWidth: "72ch" }}>{intro}</p>
      <div>
        {shown.map((e) => <EntryCard key={e.id} entry={e} allEntries={entries} />)}
      </div>
      {entries.length > PAGE && !expanded && (
        <button
          type="button"
          className="tap"
          onClick={() => setExpanded(true)}
          aria-expanded={expanded}
          style={{
            marginTop: 12, fontSize: 12.5, color: "var(--accent-2)", background: "none", border: "1px solid var(--rule)",
            borderRadius: 20, padding: "7px 16px", cursor: "pointer",
          }}
        >
          Show all {entries.length}
        </button>
      )}
    </section>
  );
}

function byDateDesc(a: EciEntry, b: EciEntry): number {
  if (!a.date && !b.date) return 0;
  if (!a.date) return 1;
  if (!b.date) return -1;
  return a.date < b.date ? 1 : a.date > b.date ? -1 : 0;
}


/** The three entry sections on a profile (PHASE4-SPEC.md §2.7), split deterministically by `entry.lane`.
 *  The profile's own `kind:"person"` entry is excluded upstream by the API (§2.7 "Profile entry"). */
export function PersonEntrySections({ name, entries }: { name: string; entries: EciEntry[] }) {
  return (
    <>
      {SECTION_LANES.map((s) => (
        <EntrySectionList
          key={s.id}
          id={s.id}
          heading={s.heading}
          intro={s.intro(name)}
          entries={entries.filter((e) => s.lanes.includes(e.lane)).slice().sort(byDateDesc)}
        />
      ))}
    </>
  );
}

