import Link from "next/link";
import { photoSrc, type PersonSummary } from "@/lib/api";
import { rupees, caseSignalColor } from "@/lib/format";
import { PartyPill, PhotoBox, Dot } from "@/components/ui";

/** The comparable directory card — the same four signals for every legislator. */
export function DirectoryCard({ p }: { p: PersonSummary }) {
  const caseColor = caseSignalColor(p.top_severity, p.total_cases);
  const noAffidavit = p.net_assets == null; // RS members file no candidate affidavit
  const seat = [p.constituency, p.current_house].filter(Boolean).join(" · ").toUpperCase();

  return (
    <Link href={`/person/${p.id}`} className="lift" style={{ textDecoration: "none", color: "var(--ink)", border: "1px solid var(--rule)", borderRadius: 12, background: "var(--card2)", overflow: "hidden", display: "block" }}>
      <div style={{ display: "flex", gap: 13, padding: 16 }}>
        <PhotoBox w={50} h={60} src={photoSrc(p.id, p.photo_url)} />
        <div style={{ minWidth: 0 }}>
          <div className="serif" style={{ fontSize: 17, fontWeight: 600, lineHeight: 1.1 }}>{p.display_name}</div>
          {p.native_name && <div className="deva" style={{ fontSize: 12, color: "var(--muted)", marginTop: 1 }}>{p.native_name}</div>}
          <div style={{ marginTop: 8 }}>
            <PartyPill party={p.current_party} />
          </div>
        </div>
      </div>
      <div style={{ display: "flex", borderTop: "1px solid var(--rule)" }}>
        <div style={{ flex: 1, padding: "10px 14px", borderRight: "1px solid var(--rule)" }}>
          <div className="mono" style={{ fontSize: 13.5, fontWeight: 500 }}>{rupees(p.net_assets)}</div>
          <div style={{ fontSize: 9.5, color: "var(--muted)", marginTop: 2 }}>ASSETS</div>
        </div>
        <div style={{ flex: 1, padding: "10px 14px" }}>
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
      </div>
      {seat && (
        <div className="mono" style={{ padding: "8px 14px", background: "var(--sunken)", fontSize: 9, letterSpacing: "0.05em", color: "var(--muted)" }}>
          {seat}
        </div>
      )}
    </Link>
  );
}
