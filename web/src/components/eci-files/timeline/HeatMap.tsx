"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { EciMonthTotal } from "@/lib/eci-files";
import { ECI_LANE_ORDER, eciLaneLabel, formatMonthKey } from "@/lib/eci-files";
import { windowAroundMonth, windowFromMonthRange } from "@/lib/eci-timeline-client";

const COL_WIDTH = 6;
const CELL_HEIGHT = 9;

/** The whole record, by month: a month x lane heat map with a box marking the visible period. Clicking a
 *  month or dragging the box picks a new window — client-side only (`onWindowChange`), same interaction
 *  as the old `DensityStrip` bars but per-lane and never a `router.push` (DESIGN-BRIEF: dragging the box
 *  "changes the period CLIENT-SIDE without a full page reload"). */
export function HeatMap({ months, from, to, onWindowChange }: {
  months: EciMonthTotal[];
  from: string;
  to: string;
  onWindowChange: (window: { from: string; to: string }) => void;
}) {
  const fromMonth = from.slice(0, 7);
  const toMonth = to.slice(0, 7);

  const laneMax = useMemo(() => {
    const max: Record<string, number> = {};
    for (const lane of ECI_LANE_ORDER) max[lane] = Math.max(1, ...months.map((m) => m.byLane[lane] ?? 0));
    return max;
  }, [months]);

  const [dragAnchor, setDragAnchor] = useState<number | null>(null);
  const [hoverIdx, setHoverIdx] = useState<number | null>(null);

  function commit(startKey: string, endKey: string) {
    onWindowChange(windowFromMonthRange(startKey, endKey));
  }
  function selectSingle(idx: number) {
    onWindowChange(windowAroundMonth(months[idx].month));
  }
  function onPointerDown(idx: number, e: React.PointerEvent) {
    e.preventDefault();
    setDragAnchor(idx);
    setHoverIdx(idx);
    (e.target as Element).setPointerCapture?.(e.pointerId);
  }
  function onPointerEnter(idx: number) {
    if (dragAnchor !== null) setHoverIdx(idx);
  }
  function onPointerUp() {
    if (dragAnchor === null) return;
    const end = hoverIdx ?? dragAnchor;
    if (dragAnchor === end) selectSingle(dragAnchor);
    else commit(months[Math.min(dragAnchor, end)].month, months[Math.max(dragAnchor, end)].month);
    setDragAnchor(null);
    setHoverIdx(null);
  }

  const selStartI = months.findIndex((m) => m.month === fromMonth);
  const selEndI = (() => {
    const i = months.findIndex((m) => m.month === toMonth);
    return i === -1 ? months.length - 1 : i;
  })();
  const previewStart = dragAnchor !== null ? Math.min(dragAnchor, hoverIdx ?? dragAnchor) : selStartI;
  const previewEnd = dragAnchor !== null ? Math.max(dragAnchor, hoverIdx ?? dragAnchor) : selEndI;
  const selLeft = previewStart >= 0 ? previewStart * COL_WIDTH : 0;
  const selWidth = previewStart >= 0 ? (previewEnd - previewStart + 1) * COL_WIDTH : 0;

  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = scrollRef.current;
    if (!el || selLeft < 0) return;
    const target = selLeft - el.clientWidth / 2 + selWidth / 2;
    el.scrollTo({ left: Math.max(0, target), behavior: "smooth" });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fromMonth, toMonth]);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14, background: "var(--card)", border: "1px solid var(--rule)", borderRadius: 14, padding: "18px 20px" }}>
      <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
        <h2 style={{ margin: 0, fontSize: 16, fontWeight: 650 }}>The whole record, by month</h2>
        <span style={{ fontSize: 12.5, color: "var(--muted)" }}>Darker = busier. Click a month, or drag to move the window.</span>
      </div>

      <div style={{ display: "flex", gap: 6 }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 2, flexShrink: 0, paddingTop: 0 }}>
          {ECI_LANE_ORDER.map((lane) => (
            <span key={lane} className="mono" style={{ height: CELL_HEIGHT, lineHeight: `${CELL_HEIGHT}px`, fontSize: 9, color: "var(--ink2)", whiteSpace: "nowrap" }}>
              {eciLaneLabel(lane).replace(" the Commission", "")}
            </span>
          ))}
        </div>
        <div ref={scrollRef} className="scroll" style={{ overflowX: "auto", overflowY: "hidden" }}>
          <div
            className="eci-density-wrap"
            onPointerUp={onPointerUp}
            onPointerLeave={() => dragAnchor === null && setHoverIdx(null)}
            style={{ display: "flex", width: months.length * COL_WIDTH, touchAction: "pan-y" }}
          >
            {selWidth > 0 && (
              <div className="eci-density-select" aria-hidden style={{ left: selLeft, width: selWidth, height: ECI_LANE_ORDER.length * (CELL_HEIGHT + 2) }} />
            )}
            {months.map((m, i) => (
              <button
                key={m.month}
                type="button"
                className="eci-heat-col"
                aria-label={`${formatMonthKey(m.month)}: ${m.total} ${m.total === 1 ? "entry" : "entries"}`}
                style={{ width: COL_WIDTH }}
                onPointerDown={(e) => onPointerDown(i, e)}
                onPointerEnter={() => onPointerEnter(i)}
                onClick={(e) => {
                  if (e.detail === 0) selectSingle(i);
                }}
              >
                {ECI_LANE_ORDER.map((lane) => {
                  const count = m.byLane[lane] ?? 0;
                  const opacity = count === 0 ? 0 : Math.min(1, 0.22 + 0.78 * (count / laneMax[lane]));
                  return (
                    <span
                      key={lane}
                      aria-hidden
                      style={{
                        display: "block", width: COL_WIDTH - 2, height: CELL_HEIGHT - 2, borderRadius: 1,
                        background: count === 0 ? "var(--rule)" : `var(--eci-lane-${lane})`, opacity: count === 0 ? 1 : opacity,
                      }}
                    />
                  );
                })}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: 6 }}>
        <span className="mono" style={{ fontSize: 10.5, color: "var(--faint)" }}>2019 – 2026</span>
        <span className="mono" style={{ fontSize: 11, color: "var(--eci-ink)" }}>{formatMonthKey(fromMonth)} – {formatMonthKey(toMonth)}</span>
      </div>
    </div>
  );
}
