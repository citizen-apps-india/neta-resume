import Link from "next/link";
import type { EciSelection } from "@/types/eci-files";
import { eciEntryHref, formatEciDate } from "@/lib/eci-files";
import { PersonAvatar } from "@/components/eci-files/PersonAvatar";

const PART_LABEL: Record<string, string> = {
  proposed: "Proposed", voted_with_majority: "Majority", recommended: "Recommended", dissented: "Dissented", search_chair: "Chaired the search",
};

function badgePart(part: string): string {
  return part === "search_chair" ? "chair" : part;
}

function Arrow() {
  return (
    <svg width="26" height="14" viewBox="0 0 26 14" fill="none" aria-hidden="true" style={{ flexShrink: 0, alignSelf: "center" }}>
      <path d="M0 7h20M14 1l6 6-6 6" stroke="var(--faint)" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

/** One selection as panel seats: who sat, how each voted (a badge, not a colour alone), an arrow, then who
 *  it produced — "selected by" as seats (C-After-Profile.dc.html §"Selected by", C-After-Selections.dc.html
 *  §"Eight selections"). Shared by the profile's `SelectedByBlock` and the selections page's
 *  `SelectionTimeline`, so a panel reads the same way in both places. `highlightSlug` rings the one
 *  appointee a profile page is about. `basePath` backs each dissent with its own source link — a dissent
 *  is a claim like any other, and the brief keeps every one sourced. */
export function SelectionSeatsRow({
  sel, highlightSlug, basePath,
}: {
  sel: EciSelection;
  highlightSlug?: string;
  basePath: string;
}) {
  const isConvention = sel.method === "executive_appointment" && sel.members.length === 0;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      <div className="eci-seat-row">
        {isConvention ? (
          <div className="eci-seat">
            <PersonAvatar name="President" photo={null} size={36} decorative />
            <span style={{ fontSize: 11, color: "var(--muted)", lineHeight: 1.25 }}>President, on the government&apos;s advice</span>
          </div>
        ) : (
          sel.members.map((m, i) => (
            <div key={i} className="eci-seat">
              <PersonAvatar name={m.name ?? m.role} photo={null} size={36} decorative />
              <span style={{ display: "flex", flexDirection: "column", gap: 1 }}>
                {m.person_slug ? (
                  <Link href={`/eci-files/people/${m.person_slug}`} style={{ fontSize: 12.5, fontWeight: 650, lineHeight: 1.2, color: "var(--ink)", textDecoration: "none" }}>
                    {m.name}
                  </Link>
                ) : (
                  <span style={{ fontSize: 12.5, fontWeight: 650, lineHeight: 1.2 }}>{m.name ?? m.role}</span>
                )}
                <span style={{ fontSize: 10, color: "var(--muted)", lineHeight: 1.25 }}>{m.role}</span>
              </span>
              <span className="eci-badge" data-part={badgePart(m.part)}>{PART_LABEL[m.part] ?? m.part}</span>
            </div>
          ))
        )}

        <Arrow />

        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {sel.appointed.map((a) => (
            <div
              key={a.person_slug}
              style={{
                display: "flex", flexDirection: "column", gap: 1, padding: "6px 12px", borderRadius: 10,
                background: a.person_slug === highlightSlug ? "color-mix(in srgb, var(--eci-ink) 10%, var(--card2))" : "transparent",
              }}
            >
              <Link href={`/eci-files/people/${a.person_slug}`} style={{ fontSize: 13.5, fontWeight: 700, color: "var(--ink)", textDecoration: "none" }}>
                {a.name}
              </Link>
              <span style={{ fontSize: 11, color: "var(--ink2)" }}>
                {a.office}{a.took_charge ? ` · took charge ${formatEciDate(a.took_charge, "day")}` : ""}
              </span>
            </div>
          ))}
        </div>
      </div>

      {sel.dissent.map((d, i) => {
        const sourceId = d.response_entry_ids[0] ?? d.entry_ids[0];
        return (
          <p key={i} style={{ fontSize: 11, color: "var(--muted)", margin: 0 }}>
            {d.name} dissented: {d.summary}
            {sourceId && (
              <>
                {" "}
                <Link href={eciEntryHref(sourceId, {}, basePath)} className="mono" style={{ color: "var(--accent-2)" }}>
                  source ↗
                </Link>
              </>
            )}
          </p>
        );
      })}
    </div>
  );
}
