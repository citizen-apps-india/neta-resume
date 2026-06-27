// The resume page — the Phase 1 vertical-slice render target.
// Server component: fetches from FastAPI server-side and renders a SourceBadge on every fact.

import { notFound } from "next/navigation";
import { getPersonResume } from "@/lib/api";
import { SourceBadge } from "@/components/SourceBadge";

function rupees(n: number): string {
  // Indian grouping + crore/lakh shorthand.
  if (n >= 1_00_00_000) return `₹${(n / 1_00_00_000).toFixed(2)} Cr`;
  if (n >= 1_00_000) return `₹${(n / 1_00_000).toFixed(2)} L`;
  return `₹${n.toLocaleString("en-IN")}`;
}

const SEVERITY_COLOR: Record<string, string> = {
  heinous: "#b00020",
  serious: "#d97706",
  minor: "#666",
};

export default async function PersonPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const resume = await getPersonResume(Number(id));
  if (!resume) notFound();

  return (
    <main>
      <h1>{resume.display_name}</h1>

      <section>
        <h2>Office history</h2>
        {resume.office_terms.length === 0 && <p style={{ color: "#999" }}>No terms recorded yet.</p>}
        <ul>
          {resume.office_terms.map((t, i) => (
            <li key={i}>
              {t.house} ({t.cycle_number}) — {t.constituency ?? t.party ?? "—"} · {t.status}
              <SourceBadge source={t.source} />
            </li>
          ))}
        </ul>
      </section>

      <section>
        <h2>Party history</h2>
        <ul>
          {resume.party_history.map((p, i) => (
            <li key={i}>
              <strong>{p.party}</strong>
              {p.joined_date ? ` · joined ${p.joined_date}` : ""}
              {p.left_date ? ` · left ${p.left_date}` : p.is_current ? " · current" : ""}
              {p.join_reason && (
                <div style={{ fontSize: "0.85rem", color: "#555" }}>
                  Joined (reported): {p.join_reason} <SourceBadge source={p.reason_source} />
                </div>
              )}
              {p.leave_reason && (
                <div style={{ fontSize: "0.85rem", color: "#555" }}>
                  Left (reported): {p.leave_reason} <SourceBadge source={p.reason_source} />
                </div>
              )}
              <SourceBadge source={p.source} />
            </li>
          ))}
        </ul>
      </section>

      <section>
        <h2>Declared wealth (ECI affidavits)</h2>
        <table style={{ borderCollapse: "collapse", width: "100%" }}>
          <thead>
            <tr style={{ textAlign: "left", borderBottom: "1px solid #ddd" }}>
              <th>Cycle</th>
              <th>Assets</th>
              <th>Liabilities</th>
              <th>Income</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {resume.wealth.map((w, i) => (
              <tr key={i} style={{ borderBottom: "1px solid #f3f3f3" }}>
                <td>{w.election_cycle}</td>
                <td>{rupees(w.total_assets)}</td>
                <td>{rupees(w.total_liabilities)}</td>
                <td>{w.self_income != null ? rupees(w.self_income) : "—"}</td>
                <td><SourceBadge source={w.source} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section>
        <h2>Criminal cases</h2>
        <p style={{ fontSize: "0.8rem", color: "#999" }}>
          Mostly pending/alleged — status shown per case; no assertion of guilt.
        </p>
        <ul>
          {resume.criminal_cases.map((c, i) => (
            <li key={i}>
              <span style={{ color: SEVERITY_COLOR[c.severity ?? "minor"], fontWeight: 600 }}>
                {(c.severity ?? "unclassified").toUpperCase()}
              </span>{" "}
              — {c.sections.join(", ")} · <em>{c.status}</em>
              {c.filed_year ? ` (${c.filed_year})` : ""}
              <SourceBadge source={c.source} />
            </li>
          ))}
        </ul>
      </section>
    </main>
  );
}
