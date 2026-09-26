"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import type {
  EciCompactEntry, EciCompactTimeline, EciEntry, EciEntryDetail, EciFilesLane, EciLaneCount, EciPersonCount, EciTopicCount,
} from "@/types/eci-files";
import { ECI_LANE_ORDER, type EciMonthTotal } from "@/lib/eci-files";
import {
  buildMonthBlocks, DAY_FOLD_THRESHOLD, fetchEciEntryDetailClient, fetchEciTimelineWindow, filterEntries, periodLabel, windowAroundDate,
} from "@/lib/eci-timeline-client";
import { ControlBar } from "@/components/eci-files/timeline/ControlBar";
import { PeriodSummary } from "@/components/eci-files/timeline/PeriodSummary";
import { EntryList } from "@/components/eci-files/timeline/EntryList";
import { HeatMap } from "@/components/eci-files/timeline/HeatMap";
import { KeyMomentsList } from "@/components/eci-files/timeline/KeyMomentsList";
import { MonthStrip } from "@/components/eci-files/timeline/MonthStrip";
import { LaneChipsRow } from "@/components/eci-files/timeline/LaneChipsRow";

export interface TimelineViewProps {
  initialWindow: { from: string; to: string };
  initialTopic?: string;
  initialPerson?: string;
  initialLanes?: EciFilesLane[];
  initialChecked?: boolean;
  initialQuery?: string;
  initialEntry?: string;
  initialTimeline: EciCompactTimeline;
  months: EciMonthTotal[];
  keyMoments: EciEntry[];
  recordTotal: number;
  basePath: string;
}

function isEditableTarget(el: EventTarget | null): boolean {
  if (!(el instanceof HTMLElement)) return false;
  const tag = el.tagName;
  return tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || el.isContentEditable;
}

/** The reworked ECI Files timeline: a control bar, a period summary + month groups on the left, and a
 *  sticky whole-record heat map + key-moments list on the right (desktop), or a month strip + lane chips
 *  + stream (phone) — see Main.dc.html / Mobile.dc.html. Owns every bit of interactive state itself; the
 *  server component that renders it (`app/eci-files/timeline/page.tsx`) only supplies the first paint. */
export function TimelineView({
  initialWindow, initialTopic, initialPerson, initialLanes, initialChecked, initialQuery, initialEntry,
  initialTimeline, months, keyMoments, recordTotal, basePath,
}: TimelineViewProps) {
  const router = useRouter();
  const pathname = usePathname();

  const [range, setRange] = useState(initialWindow);
  const [topic, setTopic] = useState(initialTopic);
  const [person, setPerson] = useState(initialPerson);
  const [activeLanes, setActiveLanes] = useState<Set<EciFilesLane>>(new Set(initialLanes && initialLanes.length > 0 ? initialLanes : ECI_LANE_ORDER));
  const [checkedOnly, setCheckedOnly] = useState(Boolean(initialChecked));
  const [query, setQuery] = useState(initialQuery ?? "");

  const [entries, setEntries] = useState<EciCompactEntry[]>(initialTimeline.entries);
  const [facets, setFacets] = useState<{ topics: EciTopicCount[]; people: EciPersonCount[]; lanes: EciLaneCount[] }>({
    topics: initialTimeline.topics, people: initialTimeline.people, lanes: initialTimeline.lanes,
  });
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState(false);

  const [expandedId, setExpandedId] = useState<string | null>(initialEntry ?? null);
  const [expandedDetail, setExpandedDetail] = useState<EciEntryDetail | null>(null);
  // Tracked by id, not a plain boolean, so a new `expandedId` is never mistaken for the previous one's
  // error — no separate "reset the error flag" setState is needed when a fetch starts.
  const [expandedErrorId, setExpandedErrorId] = useState<string | null>(null);
  const expandedError = expandedId !== null && expandedErrorId === expandedId;
  const expandedLoading = expandedId !== null && !expandedError && expandedDetail?.id !== expandedId;

  const [expandedDays, setExpandedDays] = useState<Set<string>>(new Set());
  const [expandedClusters, setExpandedClusters] = useState<Set<string>>(new Set());
  const [highlightId, setHighlightId] = useState<string | null>(null);

  const containerRef = useRef<HTMLDivElement>(null);

  // ---- fetch a new window/topic/person (client-side; never a full reload) ----
  const fetchedSigRef = useRef(`${initialTopic ?? ""}|${initialPerson ?? ""}|${initialWindow.from}|${initialWindow.to}`);
  useEffect(() => {
    const sig = `${topic ?? ""}|${person ?? ""}|${range.from}|${range.to}`;
    if (sig === fetchedSigRef.current) return;
    fetchedSigRef.current = sig;
    let cancelled = false;
    setLoading(true);
    setLoadError(false);
    fetchEciTimelineWindow({ topic, person, from: range.from, to: range.to })
      .then((data) => {
        if (cancelled) return;
        setEntries(data.entries);
        setFacets({ topics: data.topics, people: data.people, lanes: data.lanes });
      })
      .catch(() => { if (!cancelled) setLoadError(true); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [topic, person, range.from, range.to]);

  // ---- fetch the full entry when one opens in place ----
  useEffect(() => {
    // Nothing renders `expandedDetail`/`expandedErrorId` while `expandedId` is null (both derived states
    // above gate on it), so there's nothing to fetch or reset here.
    if (!expandedId) return;
    let cancelled = false;
    fetchEciEntryDetailClient(expandedId)
      .then((detail) => {
        if (cancelled) return;
        if (!detail) { setExpandedErrorId(expandedId); return; }
        setExpandedDetail(detail);
        // A jump (key moment, or a cross-reference link inside the card) can point outside the loaded
        // window — pull the window to it and clear the topic/person filters that would otherwise hide it.
        const inWindow = entries.some((e) => e.id === detail.id);
        if (!inWindow && detail.date) {
          setTopic(undefined);
          setPerson(undefined);
          setRange(windowAroundDate(detail.date));
        }
      })
      .catch(() => { if (!cancelled) setExpandedErrorId(expandedId); });
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [expandedId]);

  // The full view as query params — shared by the URL-sync effect and "Copy link" (buildShareUrl below),
  // so a copied link always reproduces exactly what's on screen, not just the topic/person/window.
  const viewParams = useCallback((entryId?: string) => {
    const params = new URLSearchParams();
    if (topic) params.set("topic", topic);
    if (person) params.set("person", person);
    params.set("from", range.from);
    params.set("to", range.to);
    if (activeLanes.size < ECI_LANE_ORDER.length) params.set("lane", ECI_LANE_ORDER.filter((l) => activeLanes.has(l)).join(","));
    if (checkedOnly) params.set("checked", "1");
    if (query) params.set("q", query);
    if (entryId) params.set("entry", entryId);
    return params;
  }, [topic, person, range, activeLanes, checkedOnly, query]);

  // ---- keep the URL in sync (router.replace — no history spam, no dependency on it for data) ----
  const lastHrefRef = useRef<string | null>(null);
  useEffect(() => {
    const qs = viewParams(expandedId ?? undefined).toString();
    const href = qs ? `${pathname}?${qs}` : pathname;
    if (href === lastHrefRef.current) return;
    lastHrefRef.current = href;
    router.replace(href, { scroll: false });
  }, [viewParams, expandedId, pathname, router]);

  const visibleEntries = useMemo(
    () => filterEntries(entries, { lanes: activeLanes, checkedOnly, query }),
    [entries, activeLanes, checkedOnly, query],
  );
  const monthBlocks = useMemo(() => buildMonthBlocks(visibleEntries), [visibleEntries]);
  const keyMomentIds = useMemo(() => new Set(keyMoments.map((k) => k.id)), [keyMoments]);

  // Flat rows in document order — used for Previous/Next and for J/K keyboard navigation.
  const flatRows = useMemo(() => {
    const rows: { kind: "entry" | "day"; id: string }[] = [];
    for (const month of monthBlocks) {
      for (const day of month.days) {
        const dayKey = `${month.key}:${day.date ?? "undated"}`;
        if (day.rawCount >= DAY_FOLD_THRESHOLD && !expandedDays.has(dayKey)) {
          rows.push({ kind: "day", id: dayKey });
        } else {
          for (const cluster of day.clusters) rows.push({ kind: "entry", id: cluster.kept.id });
        }
      }
    }
    return rows;
  }, [monthBlocks, expandedDays]);
  const flatEntryIds = useMemo(() => flatRows.filter((r) => r.kind === "entry").map((r) => r.id), [flatRows]);

  const openEntry = useCallback((id: string) => setExpandedId(id), []);
  const collapseEntry = useCallback(() => setExpandedId(null), []);

  const openIndex = expandedId ? flatEntryIds.indexOf(expandedId) : -1;
  const canPrev = openIndex > 0;
  const canNext = openIndex >= 0 && openIndex < flatEntryIds.length - 1;
  const goPrev = useCallback(() => { if (canPrev) setExpandedId(flatEntryIds[openIndex - 1]); }, [canPrev, flatEntryIds, openIndex]);
  const goNext = useCallback(() => { if (canNext) setExpandedId(flatEntryIds[openIndex + 1]); }, [canNext, flatEntryIds, openIndex]);

  const buildShareUrl = useCallback((id: string) => {
    if (typeof window === "undefined") return "";
    return `${window.location.origin}${basePath}?${viewParams(id).toString()}`;
  }, [basePath, viewParams]);

  const toggleLane = useCallback((lane: EciFilesLane) => {
    setActiveLanes((prev) => {
      const next = new Set(prev);
      if (next.has(lane)) { if (next.size > 1) next.delete(lane); } else next.add(lane);
      return next;
    });
  }, []);
  const toggleDay = useCallback((key: string) => {
    setExpandedDays((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key); else next.add(key);
      return next;
    });
  }, []);
  const toggleCluster = useCallback((keptId: string) => {
    setExpandedClusters((prev) => {
      const next = new Set(prev);
      if (next.has(keptId)) next.delete(keptId); else next.add(keptId);
      return next;
    });
  }, []);
  const jumpToKeyMoment = useCallback((id: string) => setExpandedId(id), []);

  // ---- J/K/Enter/Esc, scoped to this region: ignored while a text input/select has focus ----
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (isEditableTarget(document.activeElement)) return;
      if (e.key === "Escape") {
        if (expandedId) { e.preventDefault(); collapseEntry(); }
        return;
      }
      if (e.key !== "j" && e.key !== "k" && e.key !== "Enter") return;
      if (flatRows.length === 0) return;
      e.preventDefault();
      if (e.key === "Enter") {
        if (!highlightId) return;
        const row = flatRows.find((r) => r.id === highlightId);
        if (!row) return;
        if (row.kind === "entry") openEntry(row.id);
        else toggleDay(row.id);
        return;
      }
      const idx = highlightId ? flatRows.findIndex((r) => r.id === highlightId) : -1;
      const nextIdx = e.key === "j"
        ? Math.min(flatRows.length - 1, idx + 1)
        : Math.max(0, idx === -1 ? 0 : idx - 1);
      const row = flatRows[nextIdx];
      setHighlightId(row.id);
      const elId = row.kind === "entry" ? `eci-row-${row.id}` : `eci-row-day:${row.id}`;
      document.getElementById(elId)?.scrollIntoView({ block: "nearest" });
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [flatRows, highlightId, expandedId, collapseEntry, openEntry, toggleDay]);

  const label = periodLabel(range.from, range.to);

  return (
    <div ref={containerRef} aria-label="Timeline" style={{ display: "flex", flexDirection: "column", gap: 18 }}>
      <div className="mono" style={{ fontSize: 13, color: "var(--muted)" }}>
        {recordTotal} sourced entries · 2019–2026
        {loading && " · loading…"}
        {loadError && " · the record hasn't loaded — try again in a moment"}
      </div>

      {/* Desktop control bar + two-column layout */}
      <div className="eci-tl-desktop">
        <ControlBar
          topics={facets.topics}
          people={facets.people}
          lanes={facets.lanes}
          topic={topic}
          person={person}
          query={query}
          checkedOnly={checkedOnly}
          activeLanes={activeLanes}
          onTopicChange={setTopic}
          onPersonChange={setPerson}
          onQueryChange={setQuery}
          onCheckedOnlyChange={setCheckedOnly}
          onToggleLane={toggleLane}
        />
        <div className="eci-tl-grid">
          <main style={{ display: "flex", flexDirection: "column", minWidth: 0 }}>
            <PeriodSummary periodLabel={label} entries={entries} />
            <EntryList
              monthBlocks={monthBlocks}
              expandedId={expandedId}
              expandedDetail={expandedDetail}
              expandedLoading={expandedLoading}
              expandedError={expandedError}
              keyMomentIds={keyMomentIds}
              onOpenEntry={openEntry}
              onCollapse={collapseEntry}
              onPrev={goPrev}
              onNext={goNext}
              canPrev={canPrev}
              canNext={canNext}
              expandedDays={expandedDays}
              onToggleDay={toggleDay}
              expandedClusters={expandedClusters}
              onToggleCluster={toggleCluster}
              highlightId={highlightId}
              buildShareUrl={buildShareUrl}
            />
          </main>
          <aside className="eci-tl-aside" style={{ display: "flex", flexDirection: "column", gap: 18 }}>
            <HeatMap months={months} from={range.from} to={range.to} onWindowChange={setRange} />
            <KeyMomentsList moments={keyMoments} onJump={jumpToKeyMoment} />
          </aside>
        </div>
      </div>

      {/* Phone: month strip + lane chips + stream (Mobile.dc.html) */}
      {/* `display` stays in the .eci-tl-mobile rule (globals.css) — an inline `display` here would win
          over the media query and show both layouts at once. */}
      <div className="eci-tl-mobile" style={{ flexDirection: "column", gap: 12 }}>
        <MonthStrip months={months} from={range.from} to={range.to} onWindowChange={setRange} />
        <LaneChipsRow lanes={facets.lanes} active={activeLanes} onToggle={toggleLane} short />
        <EntryList
          monthBlocks={monthBlocks}
          expandedId={expandedId}
          expandedDetail={expandedDetail}
          expandedLoading={expandedLoading}
          expandedError={expandedError}
          keyMomentIds={keyMomentIds}
          onOpenEntry={openEntry}
          onCollapse={collapseEntry}
          onPrev={goPrev}
          onNext={goNext}
          canPrev={canPrev}
          canNext={canNext}
          expandedDays={expandedDays}
          onToggleDay={toggleDay}
          expandedClusters={expandedClusters}
          onToggleCluster={toggleCluster}
          highlightId={highlightId}
          buildShareUrl={buildShareUrl}
        />
      </div>
    </div>
  );
}
