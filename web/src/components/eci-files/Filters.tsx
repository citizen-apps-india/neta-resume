import Link from "next/link";
import type { EciTopicCount, EciPersonCount, EciLaneCount } from "@/types/eci-files";
import { eciLaneLabel } from "@/lib/eci-files";

function buildHref(base: string, cur: Record<string, string | undefined>, patch: Record<string, string | undefined>) {
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

/** Lane, topic and person filter pills. Plain links (no client JS) — the current selection is
 *  server-rendered from `searchParams`. `preserve` carries any params a filter change must not drop
 *  (the timeline's `from`/`to` window — REDESIGN-SPEC §"Filters": "without losing the current window"). */
export function Filters({
  basePath, lanes, topics, people, lane, topic, person, preserve,
}: {
  basePath: string;
  lanes?: EciLaneCount[];
  topics: EciTopicCount[];
  people: EciPersonCount[];
  lane?: string;
  topic?: string;
  person?: string;
  preserve?: Record<string, string | undefined>;
}) {
  const cur = { ...preserve, lane, topic, person };
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: 20 }}>
      {lanes && lanes.length > 0 && (
        <div style={{ display: "flex", gap: 7, flexWrap: "wrap" }}>
          <Pill label="All lanes" active={!lane} href={buildHref(basePath, cur, { lane: undefined })} />
          {lanes.map((l) => (
            <Pill
              key={l.lane}
              label={`${eciLaneLabel(l.lane)} (${l.count})`}
              active={lane === l.lane}
              href={buildHref(basePath, cur, { lane: l.lane })}
            />
          ))}
        </div>
      )}
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
