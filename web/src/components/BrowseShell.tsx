import { SiteHeader } from "@/components/SiteHeader";
import { LegislatorBrowser } from "@/components/LegislatorBrowser";
import { type PersonSummary } from "@/lib/api";

/** Page chrome shared by the Lok Sabha / Rajya Sabha / Directory browse pages. */
export function BrowseShell({
  title,
  intro,
  people,
  scope,
  error,
  initialQuery = "",
  defaultState,
}: {
  title: string;
  intro: string;
  people: PersonSummary[];
  scope: "all" | "ls" | "rs" | "state";
  error: boolean;
  initialQuery?: string;
  defaultState?: string;
}) {
  return (
    <>
      <SiteHeader />
      <main style={{ maxWidth: 1120, margin: "0 auto", padding: "28px clamp(14px,4vw,28px) 64px", width: "100%" }}>
        <h1 className="serif" style={{ fontSize: "clamp(26px,5.5vw,34px)", fontWeight: 500, letterSpacing: "-0.02em", margin: "0 0 6px" }}>
          {title}
        </h1>
        <p style={{ fontSize: 15, color: "var(--ink2)", margin: "0 0 24px", maxWidth: "64ch" }}>{intro}</p>
        {error ? (
          <div style={{ padding: "48px 24px", textAlign: "center", color: "var(--muted)", fontSize: 14, border: "1px solid var(--rule)", borderRadius: 14 }}>
            The API isn&rsquo;t reachable right now. Please try again shortly.
          </div>
        ) : (
          <LegislatorBrowser people={people} scope={scope} initialQuery={initialQuery} defaultState={defaultState} />
        )}
      </main>
    </>
  );
}
