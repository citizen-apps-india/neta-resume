import Link from "next/link";
import { SiteHeader } from "@/components/SiteHeader";
import { getElections, type Election } from "@/lib/api";
import { pretty, year } from "@/lib/format";

export const dynamic = "force-dynamic";
export const metadata = { title: "Elections", description: "Indian elections and their winners — Lok Sabha, Rajya Sabha and state assemblies — with sourced candidate records and results." };

const LEVEL_LABEL: Record<string, string> = { national: "National", state: "State", municipal: "Municipal" };

function LevelChip({ level }: { level: string }) {
  return (
    <span className="mono" style={{ fontSize: 9.5, fontWeight: 600, letterSpacing: "0.06em", textTransform: "uppercase", padding: "3px 9px", borderRadius: 5, background: "var(--accent-soft)", color: "var(--accent-soft-fg)" }}>
      {LEVEL_LABEL[level] ?? level}
    </span>
  );
}

function PastCard({ e }: { e: Election }) {
  return (
    <Link href={`/elections/${e.eci_election_id}`} className="lift" style={{ display: "block", textDecoration: "none", color: "var(--ink)", border: "1px solid var(--rule)", borderRadius: 12, background: "var(--card2)", padding: "18px 20px" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 9, marginBottom: 10 }}>
        <LevelChip level={e.level} />
        {e.election_date && <span className="mono" style={{ fontSize: 11, color: "var(--muted)" }}>{pretty(e.election_date)}</span>}
      </div>
      <div className="serif" style={{ fontSize: 17, fontWeight: 600, lineHeight: 1.15 }}>{e.name}</div>
      <div style={{ display: "flex", alignItems: "center", gap: 14, marginTop: 12, fontSize: 12.5, color: "var(--muted)" }}>
        <span><strong className="mono" style={{ color: "var(--ink)" }}>{e.winner_count.toLocaleString("en-IN")}</strong> winners</span>
        {e.seats && <span>of {e.seats} seats</span>}
        <span style={{ marginLeft: "auto", color: "var(--accent)", fontWeight: 600 }}>Results →</span>
      </div>
    </Link>
  );
}

function UpcomingCard({ e }: { e: Election }) {
  return (
    <div style={{ border: "1px dashed var(--border2)", borderRadius: 12, background: "var(--sunken)", padding: "18px 20px" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 9, marginBottom: 10 }}>
        <LevelChip level={e.level} />
        <span className="mono" style={{ fontSize: 11, color: "var(--muted)" }}>Expected {e.election_date ? year(e.election_date) : "TBA"}</span>
      </div>
      <div className="serif" style={{ fontSize: 17, fontWeight: 600, lineHeight: 1.15 }}>{e.name}</div>
      {e.note && <div style={{ fontSize: 12, color: "var(--faint)", marginTop: 8 }}>{e.note}</div>}
    </div>
  );
}

export default async function ElectionsPage() {
  let elections: Election[] = [];
  let error = false;
  try {
    elections = await getElections();
  } catch {
    error = true;
  }
  const upcoming = elections.filter((e) => e.status === "upcoming");
  const past = elections.filter((e) => e.status === "past");
  const grid: React.CSSProperties = { display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(min(100%, 300px), 1fr))", gap: 16, alignItems: "stretch" };

  return (
    <>
      <SiteHeader />
      <main style={{ maxWidth: 1120, margin: "0 auto", padding: "28px clamp(14px,4vw,28px) 64px", width: "100%" }}>
        <h1 className="serif" style={{ fontSize: "clamp(26px,5.5vw,34px)", fontWeight: 500, letterSpacing: "-0.02em", margin: "0 0 6px" }}>
          Elections <span aria-hidden>🎉</span>
        </h1>
        <p style={{ fontSize: 15, color: "var(--ink2)", margin: "0 0 28px", maxWidth: "64ch" }}>
          A celebration of democracy — India&rsquo;s elections across the national, state and municipal levels. Open a past election to browse its winners with the same comparable signals as the directory. Losing candidates and vote margins are coming next.
        </p>

        {error ? (
          <div style={{ padding: "48px 24px", textAlign: "center", color: "var(--muted)", fontSize: 14, border: "1px solid var(--rule)", borderRadius: 14 }}>
            The API isn&rsquo;t reachable right now. Please try again shortly.
          </div>
        ) : (
          <>
            {upcoming.length > 0 && (
              <section style={{ marginBottom: 36 }}>
                <h2 className="mono" style={{ fontSize: 12, letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--faint)", margin: "0 0 14px" }}>Upcoming</h2>
                <div style={grid}>
                  {upcoming.map((e) => <UpcomingCard key={e.eci_election_id ?? e.name} e={e} />)}
                </div>
              </section>
            )}
            <section>
              <h2 className="mono" style={{ fontSize: 12, letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--faint)", margin: "0 0 14px" }}>Results · Past elections</h2>
              <div style={grid}>
                {past.map((e) => <PastCard key={e.eci_election_id} e={e} />)}
              </div>
            </section>
          </>
        )}
      </main>
    </>
  );
}
