import type { Metadata } from "next";
import { Suspense } from "react";
import Link from "next/link";
import { notFound } from "next/navigation";
import { SiteHeader } from "@/components/SiteHeader";
import { EciRuleDiffSkeleton } from "@/components/skeletons";
import { RuleDiffView } from "@/components/eci-files/views/RuleDiffView";
import { EntryRefLink } from "@/components/eci-files/views/EntryRefLink";
import { DrawerFromParam } from "@/components/eci-files/views/DrawerFromParam";
import { CrossLinks } from "@/components/eci-files/views/CrossLinks";
import { getEciRuleDiff } from "@/lib/api";
import { ECI_LOAD_FAILED_MESSAGE, loadEciItem } from "@/lib/eci-files";

type Params = { diff: string };

export async function generateMetadata({ params }: { params: Promise<Params> }): Promise<Metadata> {
  const { diff } = await params;
  const d = await getEciRuleDiff(diff).catch(() => null);
  return {
    title: d ? `${d.title} · Rule changes · ECI Files` : "Rule diff not found · ECI Files",
    description: d ? `Before and after: ${d.title}.` : undefined,
    robots: { index: false, follow: false },
  };
}

function hostOf(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

async function DiffBody({ id, entry }: { id: string; entry?: string }) {
  const result = await loadEciItem(() => getEciRuleDiff(id));
  if (result.status === "not_found") notFound();
  if (result.status === "error") {
    return <p style={{ color: "var(--muted)", padding: "24px 4px" }}>{ECI_LOAD_FAILED_MESSAGE}</p>;
  }
  const d = result.data;

  const basePath = `/eci-files/rules/${id}`;

  return (
    <>
      <div style={{ marginBottom: 14 }}>
        <Link href="/eci-files/rules" className="mono" style={{ fontSize: 12, color: "var(--muted)", textDecoration: "none" }}>← Rule changes</Link>
      </div>
      <h1 className="serif" style={{ fontSize: "clamp(24px,4.6vw,32px)", fontWeight: 500, letterSpacing: "-0.02em", margin: "0 0 6px" }}>{d.title}</h1>
      <div style={{ fontSize: 13.5, color: "var(--muted)", marginBottom: 6 }}>{d.document}</div>
      <div style={{ fontSize: 12.5, marginBottom: 22 }}>
        <span style={{ color: "var(--muted)" }}>Rule entry: </span>
        <EntryRefLink
          entry={{ id: d.rule_entry.id, title: d.rule_entry.title, date: d.rule_entry.date, date_precision: d.rule_entry.date_precision, status: d.rule_entry.status, check_status: d.rule_entry.check_status }}
          basePath={basePath}
        />
      </div>

      <RuleDiffView diff={d} />

      <section style={{ marginTop: 26 }}>
        <div style={{ marginBottom: 14 }}>
          <div className="mono" style={{ fontSize: 9.5, letterSpacing: "0.06em", color: "var(--faint)", marginBottom: 6 }}>SOURCES</div>
          <ul style={{ listStyle: "none", margin: 0, padding: 0, display: "flex", flexDirection: "column", gap: 6 }}>
            {d.source_urls.map((url) => (
              <li key={url}>
                <a href={url} target="_blank" rel="noopener noreferrer" title={url} style={{ fontSize: 12.5, color: "var(--accent-2)", textDecoration: "none" }}>
                  {hostOf(url)} ↗
                </a>
              </li>
            ))}
          </ul>
        </div>
        {d.note ? (
          <details style={{ border: "1px solid var(--rule)", borderRadius: 12, background: "var(--card2)", padding: "12px 16px" }}>
            <summary className="mono" style={{ cursor: "pointer", fontSize: 12.5, fontWeight: 650, color: "var(--ink)" }}>About this text</summary>
            <p style={{ fontSize: 13, color: "var(--ink2)", lineHeight: 1.6, margin: "10px 0 0" }}>{d.note}</p>
            {d.related.length > 0 && (
              <div style={{ marginTop: 10 }}>
                <div className="mono" style={{ fontSize: 9.5, letterSpacing: "0.06em", color: "var(--faint)", marginBottom: 6 }}>RELATED</div>
                <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                  {d.related.map((r) => (
                    <EntryRefLink key={r.id} entry={r} basePath={basePath} />
                  ))}
                </div>
              </div>
            )}
          </details>
        ) : d.related.length > 0 && (
          <div>
            <div className="mono" style={{ fontSize: 9.5, letterSpacing: "0.06em", color: "var(--faint)", marginBottom: 6 }}>RELATED ENTRIES</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {d.related.map((r) => (
                <EntryRefLink key={r.id} entry={r} basePath={basePath} />
              ))}
            </div>
          </div>
        )}
      </section>

      {entry && (
        <Suspense fallback={null}>
          <DrawerFromParam id={entry} basePath={basePath} />
        </Suspense>
      )}
    </>
  );
}

export default async function EciRuleDiffPage({ params, searchParams }: { params: Promise<Params>; searchParams: Promise<{ entry?: string }> }) {
  const { diff } = await params;
  const { entry } = await searchParams;
  return (
    <>
      <SiteHeader />
      <main style={{ maxWidth: 900, margin: "0 auto", padding: "28px clamp(14px,4vw,28px) 72px", width: "100%" }}>
        <Suspense fallback={<EciRuleDiffSkeleton />}>
          <DiffBody id={diff} entry={entry} />
        </Suspense>
        <CrossLinks current="/eci-files/rules" />
      </main>
    </>
  );
}
