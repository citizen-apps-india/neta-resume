import type { EciFilesLane, EciLaneCount, EciPersonCount, EciTopicCount } from "@/types/eci-files";
import { TOPIC_LABELS } from "@/components/eci-files/Filters";
import { LaneChipsRow } from "@/components/eci-files/timeline/LaneChipsRow";

/** The desktop control bar (DESIGN-BRIEF): search, person/topic dropdowns, "Checked only", lane toggle
 *  chips with counts. Every change is client state in `TimelineView` — nothing here causes a fetch by
 *  itself except the topic/person selects (server-scoped filters); the rest (lanes, checked, search)
 *  filter what's already loaded. */
export function ControlBar({
  topics, people, lanes, topic, person, query, checkedOnly, activeLanes,
  onTopicChange, onPersonChange, onQueryChange, onCheckedOnlyChange, onToggleLane,
}: {
  topics: EciTopicCount[];
  people: EciPersonCount[];
  lanes: EciLaneCount[];
  topic?: string;
  person?: string;
  query: string;
  checkedOnly: boolean;
  activeLanes: Set<EciFilesLane>;
  onTopicChange: (v: string | undefined) => void;
  onPersonChange: (v: string | undefined) => void;
  onQueryChange: (v: string) => void;
  onCheckedOnlyChange: (v: boolean) => void;
  onToggleLane: (lane: EciFilesLane) => void;
}) {
  return (
    <div role="search" style={{ display: "flex", flexDirection: "column", gap: 12, background: "var(--card)", border: "1px solid var(--rule)", borderRadius: 14, padding: "14px 16px" }}>
      <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
        <label htmlFor="eci-tl-search" style={{ position: "absolute", width: 1, height: 1, overflow: "hidden", clip: "rect(0 0 0 0)" }}>
          Search the record
        </label>
        <input
          id="eci-tl-search"
          type="search"
          placeholder="Search titles and people"
          value={query}
          onChange={(e) => onQueryChange(e.target.value)}
          style={{ flexGrow: 1, minWidth: 160, minHeight: 42, padding: "0 14px", borderRadius: 10, border: "1px solid var(--border)", fontSize: 14.5, background: "var(--sunken)", color: "var(--ink)" }}
        />
        <label htmlFor="eci-tl-person" style={{ fontSize: 12.5, color: "var(--muted)" }}>Person</label>
        <select
          id="eci-tl-person"
          value={person ?? ""}
          onChange={(e) => onPersonChange(e.target.value || undefined)}
          className="eci-select"
        >
          <option value="">Everyone</option>
          {people.map((p) => <option key={p.slug} value={p.slug}>{p.name} ({p.count})</option>)}
        </select>
        <label htmlFor="eci-tl-topic" style={{ fontSize: 12.5, color: "var(--muted)" }}>Topic</label>
        <select
          id="eci-tl-topic"
          value={topic ?? ""}
          onChange={(e) => onTopicChange(e.target.value || undefined)}
          className="eci-select"
        >
          <option value="">All topics</option>
          {topics.map((t) => <option key={t.topic} value={t.topic}>{TOPIC_LABELS[t.topic] ?? t.topic} ({t.count})</option>)}
        </select>
        <label style={{ display: "inline-flex", gap: 8, alignItems: "center", fontSize: 13.5, color: "var(--ink2)", minHeight: 42 }}>
          <input type="checkbox" checked={checkedOnly} onChange={(e) => onCheckedOnlyChange(e.target.checked)} />
          Checked only
        </label>
      </div>
      <LaneChipsRow lanes={lanes} active={activeLanes} onToggle={onToggleLane} />
    </div>
  );
}
