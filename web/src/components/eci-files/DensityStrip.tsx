"use client";

import { useMemo, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import type { EciMonthTotal } from "@/lib/eci-files";
import { formatMonthKey } from "@/lib/eci-files";

const TRACK_HEIGHT = 56;

/** First/last day of a "YYYY-MM" month, as ISO dates. */
function monthBounds(key: string): { from: string; to: string } {
  const [y, m] = key.split("-").map(Number);
  const from = `${key}-01`;
  const last = new Date(Date.UTC(y, m, 0)).getUTCDate();
  return { from, to: `${key}-${String(last).padStart(2, "0")}` };
}

/** The overview strip: one hand-drawn SVG bar per month, 2019 to today, height by entry count. Click a bar
 *  for the default ~6-month window centred on it; drag across bars to brush an exact range. Selecting a
 *  window navigates (preserving lane/topic/person, but not the open drawer — a moved window closes it).
 *  Hand-built SVG per REDESIGN-SPEC §"Charts"; no charting library. */
export function DensityStrip({ months, from, to }: { months: EciMonthTotal[]; from: string; to: string }) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const max = useMemo(() => Math.max(1, ...months.map((m) => m.total)), [months]);
  const fromMonth = from.slice(0, 7);
  const toMonth = to.slice(0, 7);

  // The drag anchor is read during render (to compute the live brush preview), so it's state, not a ref.
  const [dragAnchor, setDragAnchor] = useState<number | null>(null);
  const [hoverIdx, setHoverIdx] = useState<number | null>(null);

  function commit(startKey: string, endKey: string) {
    const params = new URLSearchParams(searchParams.toString());
    params.set("from", monthBounds(startKey).from);
    params.set("to", monthBounds(endKey).to);
    params.delete("entry");
    router.push(`${pathname}?${params.toString()}`);
  }

  function selectSingle(idx: number) {
    // Default ~6-month window centred on the clicked month (REDESIGN-SPEC: "the web asks for about 6
    // months at a time"), clamped to the record's start and to today.
    const startIdx = Math.max(0, idx - 3);
    const endIdx = Math.min(months.length - 1, idx + 2);
    commit(months[startIdx].month, months[endIdx].month);
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
  const selLeftPct = months.length > 0 && previewStart >= 0 ? (previewStart / months.length) * 100 : 0;
  const selWidthPct = months.length > 0 && previewStart >= 0 ? ((previewEnd - previewStart + 1) / months.length) * 100 : 0;

  return (
    <div style={{ marginBottom: 22 }}>
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", marginBottom: 6 }}>
        <span className="mono" style={{ fontSize: 10.5, letterSpacing: "0.08em", color: "var(--faint)" }}>
          2019 – 2026 · CLICK OR DRAG TO SET THE WINDOW
        </span>
        <span className="mono" style={{ fontSize: 11, color: "var(--eci-ink)" }}>
          {formatMonthKey(fromMonth)} – {formatMonthKey(toMonth)}
        </span>
      </div>
      <div className="eci-density-wrap" onPointerUp={onPointerUp} onPointerLeave={() => dragAnchor === null && setHoverIdx(null)}>
        {selWidthPct > 0 && (
          <div className="eci-density-select" style={{ left: `${selLeftPct}%`, width: `${selWidthPct}%` }} aria-hidden />
        )}
        <div className="eci-density-track" role="group" aria-label="Entries per month, 2019 to 2026" style={{ height: TRACK_HEIGHT }}>
          {months.map((m, i) => {
            const h = Math.max(2, Math.round((m.total / max) * (TRACK_HEIGHT - 4)));
            return (
              <button
                key={m.month}
                type="button"
                className="eci-density-bar"
                aria-label={`${formatMonthKey(m.month)}: ${m.total} ${m.total === 1 ? "entry" : "entries"}`}
                style={{ height: TRACK_HEIGHT }}
                onPointerDown={(e) => onPointerDown(i, e)}
                onPointerEnter={() => onPointerEnter(i)}
                onClick={(e) => {
                  // pointer events already commit the selection; a synthetic click (keyboard activation)
                  // has no pointer sequence, so handle it here instead.
                  if (e.detail === 0) selectSingle(i);
                }}
              >
                <svg width="100%" height={TRACK_HEIGHT} viewBox={`0 0 10 ${TRACK_HEIGHT}`} preserveAspectRatio="none">
                  <rect x={1} y={TRACK_HEIGHT - h} width={8} height={h} rx={1} fill="var(--eci-ink)" opacity={m.total === 0 ? 0.12 : 0.55} />
                </svg>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
