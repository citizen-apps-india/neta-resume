import Link from "next/link";
import type { EciTopicCount, EciPersonCount } from "@/types/eci-files";

function buildHref(base: string, cur: { topic?: string; person?: string }, patch: Record<string, string | undefined>) {
  const merged = { ...cur, ...patch };
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(merged)) if (v) p.set(k, v);
  const qs = p.toString();
  return qs ? `${base}?${qs}` : base;
}

function Pill({ label, active, href }: { label: string; active: boolean; href: string }) {
  return (
    <Link
      href={href}
      className="tap"
      style={{
        fontSize: 12, padding: "5px 12px", borderRadius: 20, textDecoration: "none",
        border: `1px solid ${active ? "var(--accent)" : "var(--rule)"}`,
        background: active ? "var(--accent-soft)" : "var(--card2)",
        color: active ? "var(--accent-soft-fg)" : "var(--ink2)",
        whiteSpace: "nowrap",
      }}
    >
      {label}
    </Link>
  );
}

/** Topic and person filter pills for the timeline. Plain links (no client JS) — the current selection
 *  is server-rendered from `searchParams`. */
export function Filters({
  basePath, topics, people, topic, person,
}: {
  basePath: string;
  topics: EciTopicCount[];
  people: EciPersonCount[];
  topic?: string;
  person?: string;
}) {
  const cur = { topic, person };
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: 20 }}>
      {topics.length > 0 && (
        <div style={{ display: "flex", gap: 7, flexWrap: "wrap" }}>
          <Pill label="All topics" active={!topic} href={buildHref(basePath, cur, { topic: undefined })} />
          {topics.map((t) => (
            <Pill
              key={t.topic}
              label={`${t.topic} (${t.count})`}
              active={topic === t.topic}
              href={buildHref(basePath, cur, { topic: t.topic })}
            />
          ))}
        </div>
      )}
      {people.length > 0 && (
        <div style={{ display: "flex", gap: 7, flexWrap: "wrap" }}>
          <Pill label="All people" active={!person} href={buildHref(basePath, cur, { person: undefined })} />
          {people.map((p) => (
            <Pill
              key={p.slug}
              label={`${p.name} (${p.count})`}
              active={person === p.slug}
              href={buildHref(basePath, cur, { person: p.slug })}
            />
          ))}
        </div>
      )}
    </div>
  );
}
