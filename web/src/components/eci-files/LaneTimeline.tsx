"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import type { EciCompactEntry, EciFilesLane } from "@/types/eci-files";
import { ECI_LANE_ORDER, ECI_STATUS_META, dateFraction, eciLaneLabel, eciStatusMeta, formatEciDate } from "@/lib/eci-files";

/** One dot's hand-drawn SVG: solid when checked, hollow (stroke-only, background-fill centre) when not —
 *  REDESIGN-SPEC §"Lanes": "A checked entry has a solid dot; an unchecked one is hollow." */
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/** Month starts inside the window, thinned to at most ~8 labels; January carries the year. */
function monthTicks(from: string, to: string): { iso: string; label: string }[] {
  const start = new Date(`${from.slice(0, 7)}-01T00:00:00Z`);
  const end = new Date(`${to}T00:00:00Z`);
  const all: { iso: string; label: string }[] = [];
  for (let d = new Date(start); d <= end; d.setUTCMonth(d.getUTCMonth() + 1)) {
    const iso = d.toISOString().slice(0, 10);
    if (iso < from) continue;
    const m = d.getUTCMonth();
    all.push({ iso, label: m === 0 || all.length === 0 ? `${MONTHS[m]} ${d.getUTCFullYear()}` : MONTHS[m] });
  }
  const step = Math.max(1, Math.ceil(all.length / 8));
  return all.filter((_, i) => i % step === 0);
}

function DotMark({ entry }: { entry: EciCompactEntry }) {
  const meta = eciStatusMeta(entry.status);
  const checked = entry.check_status === "checked";
  return (
    <svg width={14} height={14} viewBox="0 0 14 14" aria-hidden>
      <circle
        cx={7} cy={7} r={5.5}
        fill={checked ? meta.token : "var(--card)"}
        stroke={meta.token}
        strokeWidth={checked ? 0 : 2}
      />
    </svg>
  );
}

function dotAriaLabel(e: EciCompactEntry): string {
  const date = formatEciDate(e.date, e.date_precision);
  const status = ECI_STATUS_META[e.status]?.label ?? e.status;
  const checked = e.check_status === "checked" ? "" : ", not yet checked";
  return `${date} — ${e.title} (${status}${checked})`;
}

/** Move focus to the previous/next/first/last dot within the same lane row (arrow-key roving; native
 *  Enter/Space already activates the focused button). REDESIGN-SPEC §"Accessibility": "The keyboard moves
 *  between dots within a lane." */
function onDotKeyDown(e: React.KeyboardEvent<HTMLButtonElement>) {
  if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(e.key)) return;
  const row = e.currentTarget.closest<HTMLElement>("[data-eci-lane-row]");
  if (!row) return;
  const dots = Array.from(row.querySelectorAll<HTMLButtonElement>("button.eci-dot"));
  const i = dots.indexOf(e.currentTarget);
  if (i === -1) return;
  e.preventDefault();
  const target =
    e.key === "ArrowLeft" ? dots[Math.max(0, i - 1)] :
    e.key === "ArrowRight" ? dots[Math.min(dots.length - 1, i + 1)] :
    e.key === "Home" ? dots[0] : dots[dots.length - 1];
  target?.focus();
}

/** Five lanes for the current window, entries as dots at their real date; a vertical card stream on
 *  phones instead (same data, same drawer). Fetches `fields=compact` upstream — no citations/summary here,
 *  so the first paint never pulls the whole record (REDESIGN-SPEC §"Loading"). */
export function LaneTimeline({
  entries, from, to, activeId,
}: {
  entries: EciCompactEntry[];
  from: string;
  to: string;
  activeId?: string | null;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  function openEntry(id: string) {
    const params = new URLSearchParams(searchParams.toString());
    params.set("entry", id);
    router.push(`${pathname}?${params.toString()}`, { scroll: false });
  }

  const byLane = new Map<EciFilesLane, EciCompactEntry[]>();
  for (const lane of ECI_LANE_ORDER) byLane.set(lane, []);
  for (const e of entries) {
    if (!e.date) continue;
    byLane.get(e.lane)?.push(e);
  }

  const chronological = entries.filter((e) => e.date).slice().sort((a, b) => (a.date! < b.date! ? -1 : a.date! > b.date! ? 1 : 0));

  if (entries.length === 0) {
    return <p style={{ fontSize: 13.5, color: "var(--muted)", padding: "28px 4px" }}>No entries in this window.</p>;
  }

  return (
    <>
      {/* desktop/tablet: five dated lanes */}
      <div className="eci-lanes-desktop" style={{ border: "1px solid var(--rule)", borderRadius: 12, background: "var(--card)", padding: "6px clamp(10px,2vw,18px)" }}>
        {ECI_LANE_ORDER.map((lane) => {
          const laneEntries = byLane.get(lane) ?? [];
          return (
            <div key={lane} data-eci-lane-row className="eci-lane-row" style={{ display: "flex", alignItems: "center" }}>
              <div className="mono" style={{ width: 108, flexShrink: 0, fontSize: 10.5, letterSpacing: "0.04em", color: "var(--faint)", paddingRight: 8 }}>
                {eciLaneLabel(lane).toUpperCase()}
              </div>
              <div style={{ position: "relative", flex: 1, height: "100%" }}>
                {laneEntries.map((e) => (
                  <button
                    key={e.id}
                    type="button"
                    className="eci-dot"
                    style={{ left: `${dateFraction(e.date!, from, to) * 100}%`, outlineOffset: e.id === activeId ? 3 : 2 }}
                    aria-label={dotAriaLabel(e)}
                    aria-current={e.id === activeId ? "true" : undefined}
                    onClick={() => openEntry(e.id)}
                    onKeyDown={onDotKeyDown}
                  >
                    <DotMark entry={e} />
                  </button>
                ))}
              </div>
            </div>
          );
        })}
        <div style={{ display: "flex", borderTop: "1px solid var(--rule2)", marginTop: 2 }}>
          <div style={{ width: 108, flexShrink: 0 }} />
          <div style={{ position: "relative", flex: 1, height: 22 }} aria-hidden="true">
            {monthTicks(from, to).map((t) => (
              <span
                key={t.iso}
                className="mono"
                style={{ position: "absolute", left: `${dateFraction(t.iso, from, to) * 100}%`, top: 6, transform: "translateX(-50%)", fontSize: 10, color: "var(--faint)", whiteSpace: "nowrap" }}
              >
                {t.label}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* phones: vertical card stream, same window + drawer */}
      <div className="eci-lanes-mobile">
        {chronological.map((e) => {
          const meta = eciStatusMeta(e.status);
          return (
            <button
              key={e.id}
              type="button"
              onClick={() => openEntry(e.id)}
              aria-label={dotAriaLabel(e)}
              aria-current={e.id === activeId ? "true" : undefined}
              style={{
                display: "flex", alignItems: "flex-start", gap: 10, textAlign: "left", width: "100%",
                border: "1px solid var(--rule)", borderRadius: 10, background: "var(--card2)", padding: "11px 13px", cursor: "pointer",
              }}
            >
              <span style={{ marginTop: 3, flexShrink: 0 }}><DotMark entry={e} /></span>
              <span style={{ flex: 1, minWidth: 0 }}>
                <span style={{ display: "flex", alignItems: "baseline", gap: 8, flexWrap: "wrap", marginBottom: 2 }}>
                  <span className="mono" style={{ fontSize: 10.5, color: "var(--muted)" }}>{formatEciDate(e.date, e.date_precision)}</span>
                  <span className="mono" style={{ fontSize: 9.5, letterSpacing: "0.06em", color: "var(--faint)" }}>{eciLaneLabel(e.lane).toUpperCase()}</span>
                  <span className="mono" style={{ fontSize: 9.5, fontWeight: 600, color: meta.fg }}>{meta.label.toUpperCase()}</span>
                </span>
                <span className="serif" style={{ display: "block", fontSize: 13.5, fontWeight: 600, color: "var(--ink)", lineHeight: 1.35 }}>{e.title}</span>
              </span>
            </button>
          );
        })}
      </div>
    </>
  );
}
