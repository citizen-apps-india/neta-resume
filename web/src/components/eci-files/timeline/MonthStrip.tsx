"use client";

import { useEffect, useMemo, useRef } from "react";
import type { EciMonthTotal } from "@/lib/eci-files";
import { formatMonthKey } from "@/lib/eci-files";
import { windowAroundMonth } from "@/lib/eci-timeline-client";

const BAR_WIDTH = 32;
const TRACK_HEIGHT = 58;
const MONTH_ABBR = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/** Phone's month strip (Mobile.dc.html): a mini bar per month, tap to move the window, horizontal scroll
 *  standing in for "swipe for earlier" over the record's full 2019–2026 span. */
export function MonthStrip({ months, from, to, onWindowChange }: {
  months: EciMonthTotal[];
  from: string;
  to: string;
  onWindowChange: (window: { from: string; to: string }) => void;
}) {
  const fromMonth = from.slice(0, 7);
  const toMonth = to.slice(0, 7);
  const max = useMemo(() => Math.max(1, ...months.map((m) => m.total)), [months]);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    const idx = months.findIndex((m) => m.month === fromMonth);
    if (idx < 0) return;
    el.scrollTo({ left: Math.max(0, idx * BAR_WIDTH - el.clientWidth / 3), behavior: "smooth" });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fromMonth]);

  return (
    <div style={{ background: "var(--card)", border: "1px solid var(--rule)", borderRadius: 12, padding: "10px 8px 8px", display: "flex", flexDirection: "column", gap: 6 }}>
      <div style={{ display: "flex", justifyContent: "space-between", padding: "0 6px" }}>
        <span className="mono" style={{ fontSize: 10.5, color: "var(--faint)" }}>2019–2026 · swipe for earlier</span>
        <span className="mono" style={{ fontSize: 10.5, color: "var(--eci-ink)" }}>{formatMonthKey(fromMonth)} – {formatMonthKey(toMonth)}</span>
      </div>
      <div ref={scrollRef} className="scroll" style={{ overflowX: "auto" }}>
        <div style={{ display: "flex", alignItems: "flex-end", height: TRACK_HEIGHT, padding: "0 2px" }}>
          {months.map((m) => {
            const active = m.month >= fromMonth && m.month <= toMonth;
            const h = Math.max(3, Math.round((m.total / max) * (TRACK_HEIGHT - 18)));
            const [, mm] = m.month.split("-").map(Number);
            return (
              <button
                key={m.month}
                type="button"
                onClick={() => onWindowChange(windowAroundMonth(m.month))}
                aria-label={`${formatMonthKey(m.month)}: ${m.total} ${m.total === 1 ? "entry" : "entries"}`}
                style={{
                  flexShrink: 0, width: BAR_WIDTH, display: "flex", flexDirection: "column", alignItems: "center", gap: 4,
                  border: 0, background: "none", padding: 0, cursor: "pointer",
                }}
              >
                <span aria-hidden style={{ width: 18, height: h, borderRadius: 2, background: active ? "var(--eci-ink)" : "var(--border2)" }} />
                <span className="mono" style={{ fontSize: 10, color: active ? "var(--ink)" : "var(--muted)" }}>{MONTH_ABBR[mm - 1]}</span>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
