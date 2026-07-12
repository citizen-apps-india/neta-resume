import Link from "next/link";
import { photoSrc, type PersonSummary } from "@/lib/api";
import { rupees, caseSignalColor, attendancePct, attendanceColor, eduLevel } from "@/lib/format";
import { PartyPill, PhotoBox, Dot } from "@/components/ui";
import { themeColor } from "@/lib/themes";

/** The comparable directory card — the same four signals for every legislator. */
export function DirectoryCard({ p }: { p: PersonSummary }) {
  const caseColor = caseSignalColor(p.top_severity, p.total_cases);
  const noAffidavit = p.net_assets == null; // RS members file no candidate affidavit
  const seat = [p.constituency, p.current_house].filter(Boolean).join(" · ").toUpperCase();

  return (
    <Link href={`/person/${p.id}`} title={p.display_name} className="lift" style={{ textDecoration: "none", color: "var(--ink)", border: "1px solid var(--rule)", borderRadius: 12, background: "var(--card2)", overflow: "hidden", display: "flex", flexDirection: "column", height: "100%" }}>
      <div style={{ display: "flex", gap: 13, padding: 16 }}>
        <PhotoBox w={50} h={60} src={photoSrc(p.id, p.photo_url)} />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="serif" style={{ fontSize: 17, fontWeight: 600, lineHeight: 1.1, display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden", minHeight: "2.2em" }}>{p.display_name}</div>
          {p.native_name && <div className="deva" style={{ fontSize: 12, color: "var(--muted)", marginTop: 1, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{p.native_name}</div>}
          <div style={{ marginTop: 8 }}>
            <PartyPill party={p.current_party} />
          </div>
          {(() => {
            const bits = [eduLevel(p.education), p.age ? `${p.age} yrs` : null,
              p.gender ? p.gender[0].toUpperCase() + p.gender.slice(1) : null].filter(Boolean);
            return bits.length ? (
              <div style={{ marginTop: 7, fontSize: 11, color: "var(--muted)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {bits.join(" · ")}
              </div>
            ) : null;
          })()}
        </div>
      </div>
      <div style={{ display: "flex", borderTop: "1px solid var(--rule)", marginTop: "auto" }}>
        <div style={{ flex: 1, padding: "10px 14px", borderRight: "1px solid var(--rule)" }}>
          <div className="mono" style={{ fontSize: 13.5, fontWeight: 500 }}>{rupees(p.net_assets)}</div>
          <div style={{ fontSize: 9.5, color: "var(--muted)", marginTop: 2 }}>ASSETS</div>
        </div>
        <div style={{ flex: 1, padding: "10px 14px", borderRight: "1px solid var(--rule)" }}>
          {noAffidavit ? (
            <div className="mono" style={{ fontSize: 13.5, fontWeight: 500, color: "var(--faint)" }}>—</div>
          ) : (
            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <Dot color={caseColor} sq />
              <span className="mono" style={{ fontSize: 13.5, fontWeight: 500, color: caseColor }}>{p.total_cases}</span>
            </div>
          )}
          <div style={{ fontSize: 9.5, color: "var(--muted)", marginTop: 2 }}>{noAffidavit ? "NO AFFIDAVIT" : "CASES"}</div>
        </div>
        <div style={{ flex: 1, padding: "10px 14px" }}>
          <div className="mono" style={{ fontSize: 13.5, fontWeight: 500, color: attendanceColor(p.current_attendance_pct) }}>
            {attendancePct(p.current_attendance_pct)}
          </div>
          <div style={{ fontSize: 9.5, color: "var(--muted)", marginTop: 2 }}>{p.current_attendance_pct == null ? "NO RECORD" : "ATTENDANCE"}</div>
        </div>
      </div>
      {p.questions_count != null && (
        <div style={{ display: "flex", alignItems: "center", gap: 7, padding: "8px 14px", borderTop: "1px solid var(--rule)", fontSize: 12 }}>
          <span style={{ width: 8, height: 8, borderRadius: 2, background: themeColor(p.top_theme), flexShrink: 0 }} />
          <span style={{ color: "var(--ink2)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{p.top_theme ?? "—"}</span>
          <span className="mono" style={{ marginLeft: "auto", color: "var(--muted)", fontSize: 11, whiteSpace: "nowrap" }}>{p.questions_count} Q{p.questions_count === 1 ? "" : "s"}</span>
        </div>
      )}
      {seat && (
        <div className="mono" style={{ padding: "8px 14px", background: "var(--sunken)", fontSize: 9, letterSpacing: "0.05em", color: "var(--muted)" }}>
          {seat}
        </div>
      )}
    </Link>
  );
}
