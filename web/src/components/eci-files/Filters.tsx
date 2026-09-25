import Link from "next/link";
import type { EciTopicCount, EciPersonCount, EciLaneCount } from "@/types/eci-files";
import { eciLaneLabel } from "@/lib/eci-files";
import { FilterSelect } from "@/components/eci-files/FilterSelect";

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

const TOPIC_LABELS: Record<string, string> = {
  sir: "SIR", rolls: "Voter rolls", appointments: "Appointments", statements: "Statements", courts: "Courts",
  numbers: "Numbers", "it-systems": "IT systems", dissent: "Dissent", "elections-2024": "2024 election",
  "elections-2019": "2019 election", forms: "Forms", mcc: "Model Code", "turnout-data": "Turnout data",
  "evm-vvpat": "EVM & VVPAT", rules: "Rules",
};

type PillItem = { key: string; label: string; href: string; active: boolean };

/** One filter row: the busiest few as pills, the rest folded behind "More" (no client JS). The active
 *  choice always stays visible, even when it would otherwise be folded. */
function PillRow({ all, items, visible }: { all: PillItem; items: PillItem[]; visible: number }) {
  const shown = items.slice(0, visible);
  const rest = items.slice(visible);
  const activeHidden = rest.find((i) => i.active);
  return (
    <div style={{ display: "flex", gap: 7, flexWrap: "wrap", alignItems: "center" }}>
      <Pill label={all.label} active={all.active} href={all.href} />
      {shown.map((i) => <Pill key={i.key} label={i.label} active={i.active} href={i.href} />)}
      {activeHidden && <Pill label={activeHidden.label} active href={activeHidden.href} />}
      {rest.length > 0 && (
        <details className="eci-more">
          <summary className="mono" style={{ fontSize: 11.5, color: "var(--accent-2)", cursor: "pointer", padding: "5px 6px", listStyle: "none" }}>
            + {rest.length} more
          </summary>
          <div style={{ display: "flex", gap: 7, flexWrap: "wrap", marginTop: 8 }}>
            {rest.filter((i) => !i.active).map((i) => <Pill key={i.key} label={i.label} active={false} href={i.href} />)}
          </div>
        </details>
      )}
    </div>
  );
}

/** Lane, topic and person filters. Plain links: the selection is server-rendered from `searchParams`.
 *  `preserve` carries params a filter change must not drop (the timeline's `from`/`to` window). */
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
        <PillRow
          all={{ key: "all", label: "All lanes", active: !lane, href: buildHref(basePath, cur, { lane: undefined }) }}
          items={lanes.map((l) => ({ key: l.lane, label: `${eciLaneLabel(l.lane)} (${l.count})`, active: lane === l.lane, href: buildHref(basePath, cur, { lane: l.lane }) }))}
          visible={lanes.length}
        />
      )}
      {(topics.length > 0 || people.length > 0) && (
        <div style={{ display: "flex", gap: "10px 20px", flexWrap: "wrap", alignItems: "center" }}>
          {topics.length > 0 && (
            <FilterSelect
              id="eci-filter-topic"
              label="Topic"
              param="topic"
              value={topic}
              allLabel="All topics"
              options={topics.map((t) => ({ value: t.topic, label: `${TOPIC_LABELS[t.topic] ?? t.topic} (${t.count})` }))}
            />
          )}
          {people.length > 0 && (
            <FilterSelect
              id="eci-filter-person"
              label="Person"
              param="person"
              value={person}
              allLabel="All people"
              options={people.map((p) => ({ value: p.slug, label: `${p.name} (${p.count})` }))}
            />
          )}
        </div>
      )}
    </div>
  );
}
