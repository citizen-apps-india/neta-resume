import Link from "next/link";
import type { EciEntryRef, EciSelection } from "@/types/eci-files";
import { eciEntryHref, formatEciDate, regimeShortLabel } from "@/lib/eci-files";
import { PersonAvatar } from "@/components/eci-files/PersonAvatar";
import { StatusChip } from "@/components/eci-files/StatusChip";

const PART_LABEL: Record<string, string> = {
  proposed: "Proposed", voted_with_majority: "Majority", recommended: "Recommended",
  dissented: "Dissented", search_chair: "Chaired the search",
};

function CitedLine({ ids, entriesIndex, basePath }: { ids: string[]; entriesIndex: EciEntryRef[]; basePath: string }) {
  if (ids.length === 0) return null;
  const byId = new Map(entriesIndex.map((e) => [e.id, e]));
  return (
    <div className="mono" style={{ fontSize: 11, color: "var(--faint)", marginTop: 8 }}>
      Cited:{" "}
      {ids.map((id, i) => (
        <span key={id}>
          {i > 0 && ", "}
          <Link href={eciEntryHref(id, {}, basePath)} style={{ color: "var(--accent-2)" }}>{byId.get(id)?.title ?? id}</Link>
        </span>
      ))}
    </div>
  );
}

/** One selection, everywhere it's shown: `/eci-files/selections`' `SelectionList` (appointees at the
 *  top) and a profile's `SelectedByBlock` (`viewerSlug` set, appointees folded into the title instead —
 *  PHASE4-SPEC.md §2.5.1, §3 step 4: "the same card as `SelectedByBlock` with the appointees added"). */
export function SelectionCard({
  sel, entriesIndex, basePath, viewerSlug, showAppointees = true,
}: {
  sel: EciSelection;
  entriesIndex: EciEntryRef[];
  basePath: string;
  viewerSlug?: string;
  showAppointees?: boolean;
}) {
  const mine = viewerSlug ? sel.appointed.find((a) => a.person_slug === viewerSlug) : null;
  const isConvention = sel.method === "executive_appointment" && sel.members.length === 0;

  return (
    <div id={sel.id} style={{ border: "1px solid var(--rule)", borderRadius: 12, background: "var(--card2)", padding: "16px 18px", marginBottom: 14, scrollMarginTop: 90 }}>
      <div className="mono" style={{ fontSize: 9.5, letterSpacing: "0.06em", color: "var(--faint)", marginBottom: 4 }}>SELECTED BY</div>

      {showAppointees && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 10, marginBottom: 8 }}>
          {sel.appointed.map((a) => (
            <Link key={a.person_slug} href={`/eci-files/people/${a.person_slug}`} style={{ display: "flex", alignItems: "center", gap: 6, textDecoration: "none" }}>
              <PersonAvatar name={a.name} photo={a.photo} size={28} decorative />
              <span style={{ fontSize: 13.5, fontWeight: 600, color: "var(--ink)" }}>{a.name}</span>
              <span className="mono" style={{ fontSize: 10.5, color: "var(--muted)" }}>{a.office}</span>
            </Link>
          ))}
        </div>
      )}

      <div className="serif" style={{ fontSize: 16, fontWeight: 600, marginBottom: 8 }}>
        {mine ? `${mine.office} · ` : ""}{formatEciDate(sel.date, sel.date_precision)}
      </div>

      <Link
        href={`/eci-files/selections#regime-${sel.regime}`}
        className="mono"
        style={{
          display: "inline-block", fontSize: 10.5, fontWeight: 600, color: "var(--eci-ink)", textDecoration: "none",
          background: "color-mix(in srgb, var(--eci-ink) 10%, var(--card2))", border: "1px solid color-mix(in srgb, var(--eci-ink) 40%, var(--rule))",
          borderRadius: 20, padding: "3px 10px", marginBottom: 12,
        }}
      >
        {regimeShortLabel(sel.regime)}
      </Link>

      {isConvention ? (
        <p style={{ fontSize: 12.5, color: "var(--muted)", margin: "4px 0 0" }}>
          Appointed by the President on the Union government&apos;s advice. No committee existed.
        </p>
      ) : (
        sel.members.length > 0 && (
          <ul style={{ listStyle: "none", margin: "4px 0 0", padding: 0, display: "flex", flexDirection: "column", gap: 8 }}>
            {sel.members.map((m, i) => (
              <li key={i} style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                <PersonAvatar name={m.name ?? m.role} photo={null} size={24} decorative />
                {m.person_slug ? (
                  <Link href={`/eci-files/people/${m.person_slug}`} style={{ fontWeight: 600, color: "var(--ink)", textDecoration: "none", fontSize: 13 }}>
                    {m.name}
                  </Link>
                ) : (
                  <span style={{ fontSize: 13, color: "var(--ink)" }}>{m.name ?? m.role}</span>
                )}
                <span style={{ fontSize: 11.5, color: "var(--muted)" }}>{m.role}</span>
                <span className="eci-badge" data-part={m.part === "search_chair" ? "chair" : m.part}>{PART_LABEL[m.part] ?? m.part}</span>
              </li>
            ))}
          </ul>
        )
      )}

      {sel.search && (
        <div style={{ marginTop: 12, padding: "10px 12px", borderRadius: 8, background: "var(--sunken)" }}>
          <div style={{ fontSize: 12.5, color: "var(--ink2)" }}>{sel.search.by}</div>
          {sel.search.shortlist && sel.search.shortlist.length > 0 && (
            <>
              <div style={{ fontSize: 12, color: "var(--ink2)", marginTop: 6 }}>
                Shortlist of {sel.search.shortlist_size ?? sel.search.shortlist.length}: {sel.search.shortlist.join(", ")}
              </div>
              {sel.search.shortlist_source && (
                <div style={{ fontSize: 11.5, color: "var(--muted)", marginTop: 6 }}>Shortlist from {sel.search.shortlist_source}.</div>
              )}
            </>
          )}
        </div>
      )}

      {sel.dissent.map((d, i) => (
        <div key={i} style={{ marginTop: 12, border: "1px solid var(--rule)", borderRadius: 8, padding: "10px 12px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
            <StatusChip status={d.status} />
            <span style={{ fontSize: 12.5, fontWeight: 600, color: "var(--ink)" }}>{d.name}</span>
          </div>
          <p style={{ fontSize: 12.5, color: "var(--ink2)", margin: "0 0 6px" }}>{d.summary}</p>
          <div style={{ fontSize: 11.5, color: "var(--muted)" }}>Note published: {d.note_public ? "yes" : "no"}</div>
          {d.response_entry_ids.length > 0 && (
            <div style={{ fontSize: 11.5, color: "var(--muted)", marginTop: 4 }}>
              Response:{" "}
              {d.response_entry_ids.map((id, ri) => (
                <span key={id}>
                  {ri > 0 && ", "}
                  <Link href={eciEntryHref(id, {}, basePath)} style={{ color: "var(--accent-2)" }}>
                    {entriesIndex.find((e) => e.id === id)?.title ?? id}
                  </Link>
                </span>
              ))}
            </div>
          )}
        </div>
      ))}

      {sel.notes && <p style={{ fontSize: 12.5, color: "var(--muted)", marginTop: 12 }}>{sel.notes}</p>}

      <CitedLine ids={sel.entry_ids} entriesIndex={entriesIndex} basePath={basePath} />
    </div>
  );
}
