import type { EciEntryStatus, EciLaneCount, EciPersonCount, EciTopicCount } from "@/types/eci-files";
import { eciLaneLabel, eciStatusMeta } from "@/lib/eci-files";
import { FilterSelect } from "@/components/eci-files/FilterSelect";
import { EntriesSearchAndChecked } from "@/components/eci-files/front/EntriesSearchAndChecked";

const STATUSES: EciEntryStatus[] = ["documented", "reported", "claim", "response"];

// Same display names as Filters.tsx's TOPIC_LABELS — duplicated rather than exported, since that file's
// map is private to its own pill row and this page's dropdown reads differently (a plain <select>, not pills).
const TOPIC_LABELS: Record<string, string> = {
  sir: "SIR", rolls: "Voter rolls", appointments: "Appointments", statements: "Statements", courts: "Courts",
  numbers: "Numbers", "it-systems": "IT systems", dissent: "Dissent", "elections-2024": "2024 election",
  "elections-2019": "2019 election", forms: "Forms", mcc: "Model Code", "turnout-data": "Turnout data",
  "evm-vvpat": "EVM & VVPAT", rules: "Rules",
};

/** The entries page's filter card: free-text search, checked-only, and four dropdowns (lane, status,
 *  topic, person) — all four are plain `<select>`s per the approved design, unlike the lane timeline's
 *  pill row. Every control rewrites the URL and leaves the others alone (see `FilterSelect`). */
export function EntriesFilterBar({
  lanes, topics, people, lane, status, topic, person, q, checked,
}: {
  lanes: EciLaneCount[];
  topics: EciTopicCount[];
  people: EciPersonCount[];
  lane?: string;
  status?: string;
  topic?: string;
  person?: string;
  q?: string;
  checked?: boolean;
}) {
  return (
    <div
      role="search"
      style={{
        position: "relative", display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap",
        background: "var(--card)", border: "1px solid var(--rule)", borderRadius: 14, padding: "14px 16px", marginBottom: 18,
      }}
    >
      <EntriesSearchAndChecked q={q} checked={checked} />
      <FilterSelect
        id="eci-entries-lane" label="Lane" param="lane" value={lane} allLabel="All lanes"
        options={lanes.map((l) => ({ value: l.lane, label: `${eciLaneLabel(l.lane)} (${l.count})` }))}
      />
      <FilterSelect
        id="eci-entries-status" label="Status" param="status" value={status} allLabel="All statuses"
        options={STATUSES.map((s) => ({ value: s, label: eciStatusMeta(s).label }))}
      />
      {topics.length > 0 && (
        <FilterSelect
          id="eci-entries-topic" label="Topic" param="topic" value={topic} allLabel="All topics"
          options={topics.map((t) => ({ value: t.topic, label: `${TOPIC_LABELS[t.topic] ?? t.topic} (${t.count})` }))}
        />
      )}
      {people.length > 0 && (
        <FilterSelect
          id="eci-entries-person" label="Person" param="person" value={person} allLabel="Everyone"
          options={people.map((p) => ({ value: p.slug, label: `${p.name} (${p.count})` }))}
        />
      )}
    </div>
  );
}
