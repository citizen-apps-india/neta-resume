import Link from "next/link";
import { photoSrc, type PersonSummary } from "@/lib/api";
import { rupees, attendancePct, attendanceColor, caseSignalColor } from "@/lib/format";
import { PartyPill, PhotoBox } from "@/components/ui";

type Sort = "assets" | "cases" | "attendance" | "name";

const hStyle: React.CSSProperties = {
  fontSize: 10, letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--muted)", fontWeight: 500,
};

/** Dense, scannable table view of a legislator list. Columns are scope-aware — RS members file no
 *  affidavit, so their Assets/Cases columns are dropped in favour of the state they represent. Header
 *  cells for sortable fields drive the shared `sort` state (kept in sync with the Sort dropdown). */
export function LegislatorTable({
  rows, scope, sort, onSort,
}: {
  rows: PersonSummary[];
  scope: "ls" | "rs";
  sort: Sort;
  onSort: (s: Sort) => void;
}) {
  const isRS = scope === "rs";
  const cols = isRS
    ? "34px 2.3fr 1.5fr 1.4fr 0.8fr"           // # · Name · Party · State · Att.
    : "34px 2.3fr 1.5fr 1.3fr 1fr 0.9fr 0.8fr"; // # · Name · Party · Constituency · Assets · Cases · Att.
  const minW = isRS ? 560 : 780;

  const SortHead = ({ label, s }: { label: string; s: Sort }) => (
    <button
      type="button"
      onClick={() => onSort(s)}
      className="mono"
      style={{
        display: "inline-flex", alignItems: "center", gap: 4, border: "none", background: "transparent",
        cursor: "pointer", padding: 0, ...hStyle,
        color: s === sort ? "var(--ink)" : "var(--muted)", fontWeight: s === sort ? 700 : 500,
      }}
    >
      {label}{s === sort && <span aria-hidden>↓</span>}
    </button>
  );

  return (
    <div className="nr-xscroll" style={{ border: "1px solid var(--rule)", borderRadius: 10, overflow: "hidden" }}>
      <div style={{ minWidth: minW }}>
        {/* header row */}
        <div style={{ display: "grid", gridTemplateColumns: cols, gap: 12, padding: "12px 16px", background: "var(--sunken)", borderBottom: "1px solid var(--rule)", alignItems: "center" }}>
          <span className="mono" style={hStyle}>#</span>
          <SortHead label="Name" s="name" />
          <span className="mono" style={hStyle}>Party</span>
          <span className="mono" style={hStyle}>{isRS ? "State" : "Constituency"}</span>
          {!isRS && <div style={{ textAlign: "right" }}><SortHead label="Assets" s="assets" /></div>}
          {!isRS && <div style={{ textAlign: "right" }}><SortHead label="Cases" s="cases" /></div>}
          <div style={{ textAlign: "right" }}><SortHead label="Att." s="attendance" /></div>
        </div>

        {/* body rows */}
        {rows.map((p, i) => (
          <Link
            key={p.id}
            href={`/person/${p.id}`}
            title={p.display_name}
            className="liftsm"
            style={{ display: "grid", gridTemplateColumns: cols, gap: 12, padding: "10px 16px", borderBottom: "1px solid var(--rule)", alignItems: "center", textDecoration: "none", color: "var(--ink)", background: i % 2 ? "var(--card)" : "var(--card2)" }}
          >
            <span className="mono" style={{ fontSize: 11, color: "var(--faint)" }}>{i + 1}</span>
            <div style={{ display: "flex", alignItems: "center", gap: 10, minWidth: 0 }}>
              <PhotoBox w={28} h={34} src={photoSrc(p.id, p.photo_url)} />
              <div style={{ minWidth: 0 }}>
                <div className="serif" style={{ fontSize: 14, fontWeight: 600, lineHeight: 1.15, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{p.display_name}</div>
                {p.native_name && <div className="deva" style={{ fontSize: 11, color: "var(--muted)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{p.native_name}</div>}
              </div>
            </div>
            <div style={{ minWidth: 0, overflow: "hidden" }}><PartyPill party={p.current_party} /></div>
            <span style={{ fontSize: 12.5, color: "var(--muted)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{p.constituency ?? "—"}</span>
            {!isRS && <span className="mono" style={{ fontSize: 13, textAlign: "right", color: p.net_assets == null ? "var(--faint)" : "var(--ink)" }}>{rupees(p.net_assets)}</span>}
            {!isRS && <span className="mono" style={{ fontSize: 13, textAlign: "right", color: p.net_assets == null ? "var(--faint)" : caseSignalColor(p.top_severity, p.total_cases) }}>{p.net_assets == null ? "—" : p.total_cases}</span>}
            <span className="mono" style={{ fontSize: 13, textAlign: "right", color: attendanceColor(p.current_attendance_pct) }}>{attendancePct(p.current_attendance_pct)}</span>
          </Link>
        ))}
      </div>
    </div>
  );
}
