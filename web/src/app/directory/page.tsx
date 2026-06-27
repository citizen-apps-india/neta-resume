import { SiteHeader } from "@/components/SiteHeader";
import { SearchBox } from "@/components/SearchBox";
import { DirectoryCard } from "@/components/DirectoryCard";
import { listPersons, searchPersons, type PersonSummary } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function Directory({
  searchParams,
}: {
  searchParams: Promise<{ q?: string; house?: string }>;
}) {
  const { q, house } = await searchParams;
  let people: PersonSummary[] = [];
  let error = false;
  try {
    if (q && q.trim().length >= 2) {
      people = await searchPersons(q.trim());
      if (house) people = people.filter((p) => p.current_house === house);
    } else {
      people = await listPersons(house ? 300 : 120, 0, house);
    }
  } catch {
    error = true;
  }

  return (
    <>
      <SiteHeader />
      <main style={{ maxWidth: 1080, margin: "0 auto", padding: "32px 28px 72px", width: "100%" }}>
        <h1 className="serif" style={{ fontSize: 34, fontWeight: 500, letterSpacing: "-0.02em", margin: "0 0 6px" }}>
          Directory
        </h1>
        <p style={{ fontSize: 15, color: "var(--ink2)", margin: "0 0 24px", maxWidth: "60ch" }}>
          Find your representative. Every card carries the same four signals, so any two people are comparable at a glance.
        </p>

        <div style={{ border: "1px solid var(--border)", borderRadius: 14, overflow: "hidden", background: "var(--bg)", boxShadow: "0 24px 60px -32px var(--shadow)" }}>
          <div style={{ padding: "22px 26px", borderBottom: "1px solid var(--rule)", background: "var(--card)" }}>
            <div style={{ maxWidth: 560 }}>
              <SearchBox big initial={q ?? ""} placeholder="Search legislators by name, constituency or party…" />
            </div>
          </div>

          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "14px 26px", background: "var(--sunken)", borderBottom: "1px solid var(--rule)" }}>
            <span style={{ fontSize: 12.5, color: "var(--muted)" }}>
              <strong className="mono" style={{ color: "var(--ink)" }}>{people.length}</strong>{" "}
              {q ? `result${people.length === 1 ? "" : "s"} for "${q}"` : "legislators"}
              {house ? ` · ${house}` : ""}
            </span>
            <span className="mono" style={{ fontSize: 10.5, color: "var(--muted)" }}>
              {q ? "SORT: RELEVANCE" : "SORT: ASSETS ↓"}
            </span>
          </div>

          <div style={{ padding: 26, background: "var(--bg)" }}>
            {error ? (
              <Empty msg="The API isn't reachable. Start it with `uv run uvicorn neta_api.main:app` and retry." />
            ) : people.length === 0 ? (
              <Empty msg={q ? `No legislators match "${q}" yet.` : "No legislators ingested yet."} />
            ) : (
              <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 16 }}>
                {people.map((p) => (
                  <DirectoryCard key={p.id} p={p} />
                ))}
              </div>
            )}
          </div>
        </div>
      </main>
    </>
  );
}

function Empty({ msg }: { msg: string }) {
  return (
    <div style={{ padding: "48px 24px", textAlign: "center", color: "var(--muted)", fontSize: 14 }}>
      {msg}
    </div>
  );
}
