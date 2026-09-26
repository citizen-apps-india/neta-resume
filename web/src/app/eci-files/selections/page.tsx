import type { Metadata } from "next";
import { Suspense } from "react";
import Link from "next/link";
import { SiteHeader } from "@/components/SiteHeader";
import { SectionHero } from "@/components/parliament/SectionHero";
import { RegimeCompare } from "@/components/eci-files/RegimeCompare";
import { SelectionGraph } from "@/components/eci-files/SelectionGraph";
import { SelectionCard } from "@/components/eci-files/SelectionCard";
import { EntryDrawer } from "@/components/eci-files/EntryDrawer";
import { EntryDetail } from "@/components/eci-files/EntryDetail";
import { getEciEntry, getEciSelections, type EciSelections } from "@/lib/api";
import { formatEciDate, eciEntryHref } from "@/lib/eci-files";

export const metadata: Metadata = {
  title: "How they were chosen · ECI Files",
  description: "Eight selections from 2019 to 2025, who sat on each panel, and the two recorded dissents.",
  robots: { index: false, follow: false },
};

const BASE_PATH = "/eci-files/selections";

async function SelectionsBody({ entry }: { entry?: string }) {
  let data: EciSelections | null = null;
  try {
    data = await getEciSelections();
  } catch {
    data = null;
  }

  if (!data) {
    return (
      <p style={{ color: "var(--muted)", padding: "24px 4px" }}>
        The record hasn&apos;t loaded — try again in a moment.
      </p>
    );
  }
  const selections: EciSelections = data;

  return (
    <>
      <RegimeCompare regimes={selections.regimes} entriesIndex={selections.entries_index} />

      <SelectionGraph selections={selections.selections} regimes={selections.regimes} />

      <section id="selection-list" style={{ marginTop: 28 }}>
        <h2 className="serif" style={{ fontSize: 20, fontWeight: 600, margin: "0 0 12px" }}>Every selection</h2>
        {selections.selections.map((sel) => (
          <SelectionCard key={sel.id} sel={sel} entriesIndex={selections.entries_index} basePath={BASE_PATH} />
        ))}
      </section>

      <section id="departures" style={{ marginTop: 28 }}>
        <h2 className="serif" style={{ fontSize: 20, fontWeight: 600, margin: "0 0 12px" }}>Departures</h2>
        <table className="eci-state-table">
          <caption style={{ textAlign: "left", fontSize: 12.5, color: "var(--muted)", padding: "0 0 10px" }}>
            How each commissioner&apos;s tenure ended, where it ended before a full term.
          </caption>
          <thead>
            <tr>
              <th scope="col">Date</th>
              <th scope="col">Name</th>
              <th scope="col">Office</th>
              <th scope="col">How it ended</th>
              <th scope="col">Cited</th>
            </tr>
          </thead>
          <tbody>
            {selections.departures.map((d, i) => (
              <tr key={i}>
                <td className="mono" style={{ fontSize: 12 }}>{formatEciDate(d.date, "day")}</td>
                <td>
                  <Link href={`/eci-files/people/${d.person_slug}`} style={{ color: "var(--ink)", textDecoration: "none", fontWeight: 600 }}>{d.name}</Link>
                </td>
                <td style={{ fontSize: 12.5 }}>{d.office}</td>
                <td style={{ fontSize: 12.5 }}>
                  {d.how === "resigned" ? "Resigned" : "Tenure ended"}
                  {d.notes && <div style={{ fontSize: 11.5, color: "var(--muted)", marginTop: 3 }}>{d.notes}</div>}
                </td>
                <td className="mono" style={{ fontSize: 10.5, color: "var(--faint)" }}>
                  {d.entry_ids.map((id, ei) => (
                    <span key={id}>
                      {ei > 0 && ", "}
                      <Link href={eciEntryHref(id, {}, BASE_PATH)} style={{ color: "var(--accent-2)" }}>{selections.entries_index.find((e) => e.id === id)?.title ?? id}</Link>
                    </span>
                  ))}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      {selections.gaps.length > 0 && (
        <section style={{ marginTop: 28 }}>
          <h2 className="serif" style={{ fontSize: 18, fontWeight: 600, margin: "0 0 10px" }}>What the record doesn&apos;t show</h2>
          <ul style={{ margin: 0, paddingLeft: 20, color: "var(--muted)", fontSize: 13, lineHeight: 1.7 }}>
            {selections.gaps.map((g, i) => <li key={i}>{g}</li>)}
          </ul>
        </section>
      )}

      {entry && (
        <Suspense fallback={null}>
          <SelectionsDrawer id={entry} />
        </Suspense>
      )}
    </>
  );
}

async function SelectionsDrawer({ id }: { id: string }) {
  const full = await getEciEntry(id).catch(() => null);
  if (!full) return null;
  return (
    <EntryDrawer>
      <EntryDetail entry={full} basePath={BASE_PATH} />
    </EntryDrawer>
  );
}

export default async function EciSelectionsPage({ searchParams }: { searchParams: Promise<{ entry?: string }> }) {
  const { entry } = await searchParams;
  return (
    <>
      <SiteHeader />
      <main style={{ maxWidth: 1080, margin: "0 auto", padding: "28px clamp(14px,4vw,28px) 72px", width: "100%" }}>
        <SectionHero
          eyebrow="ECI FILES · SELECTIONS"
          title="How the commissioners were chosen"
          subtitle="Eight selections from 2019 to 2025, who sat on each panel, and the two recorded dissents. Every line cites an entry."
          backHref="/eci-files/people"
          backLabel="People"
        />
        <Suspense fallback={<p style={{ color: "var(--muted)" }}>Loading…</p>}>
          <SelectionsBody entry={entry} />
        </Suspense>
      </main>
    </>
  );
}
