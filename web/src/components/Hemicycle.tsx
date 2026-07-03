"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { type PersonSummary } from "@/lib/api";
import { partyColor } from "@/lib/partyColors";

const TOTAL: Record<"ls" | "rs", number> = { ls: 543, rs: 245 };
const LEGEND_MAX = 14;

/** Distribute n seats across concentric arc rows (outer rows longer -> more seats), returning each seat's
 *  radius-fraction + angle, sorted left(π)->right(0) so parties fill as vertical wedges. */
function computeSeats(n: number): { rad: number; angle: number }[] {
  if (n <= 0) return [];
  const rows = Math.max(4, Math.round(Math.sqrt(n / 2.2)));
  const r0 = 0.52; // inner radius fraction
  const radii = Array.from({ length: rows }, (_, i) => (rows === 1 ? 1 : r0 + (1 - r0) * (i / (rows - 1))));
  const wsum = radii.reduce((a, b) => a + b, 0);
  const per = radii.map((r) => Math.max(1, Math.floor((n * r) / wsum)));
  let assigned = per.reduce((a, b) => a + b, 0);
  let i = rows - 1;
  while (assigned < n) { per[i]++; assigned++; i = i === 0 ? rows - 1 : i - 1; }
  const seats: { rad: number; angle: number }[] = [];
  for (let row = 0; row < rows; row++) {
    const k = per[row];
    for (let j = 0; j < k; j++) {
      const t = k === 1 ? 0.5 : j / (k - 1);
      seats.push({ rad: radii[row], angle: Math.PI * (1 - t) });
    }
  }
  return seats.sort((a, b) => b.angle - a.angle);
}

/** Election-night parliament seat-map: one dot per member, grouped + coloured by party. */
export function Hemicycle({
  members, activeIds, scope,
}: {
  members: PersonSummary[];
  activeIds: Set<number>;
  scope: "ls" | "rs";
}) {
  const router = useRouter();
  const [hover, setHover] = useState<PersonSummary | null>(null);

  // Order members into party blocs (largest party first), then map onto seats left->right.
  const { ordered, partyList } = useMemo(() => {
    const groups = new Map<string, PersonSummary[]>();
    for (const m of members) {
      const key = m.current_party ?? "Independent / Other";
      const arr = groups.get(key);
      if (arr) arr.push(m); else groups.set(key, [m]);
    }
    const pl = [...groups.entries()].sort((a, b) => b[1].length - a[1].length);
    return { ordered: pl.flatMap(([, ms]) => ms), partyList: pl };
  }, [members]);

  const seats = useMemo(() => computeSeats(ordered.length), [ordered.length]);

  const VW = 1000, VH = 500, cx = VW / 2, cy = 484, outerR = 466, r0 = 0.52;
  const rows = Math.max(4, Math.round(Math.sqrt(Math.max(1, ordered.length) / 2.2)));
  const dotR = Math.max(3, Math.min(11, (outerR * (1 - r0) / rows) * 0.42));
  const total = TOTAL[scope];

  const legendMain = partyList.slice(0, LEGEND_MAX);
  const restCount = partyList.slice(LEGEND_MAX).reduce((a, [, ms]) => a + ms.length, 0);

  return (
    <div>
      {/* header: seats filled + hover caption */}
      <div style={{ display: "flex", flexWrap: "wrap", alignItems: "baseline", justifyContent: "space-between", gap: 8, marginBottom: 10 }}>
        <span className="mono" style={{ fontSize: 11.5, color: "var(--muted)" }}>
          <strong style={{ color: "var(--ink)" }}>{ordered.length.toLocaleString("en-IN")}</strong> of {total} seats
        </span>
        <span style={{ fontSize: 12.5, color: hover ? "var(--ink)" : "var(--faint)", minHeight: 18, textAlign: "right" }}>
          {hover
            ? <>{hover.display_name} — <span style={{ color: "var(--muted)" }}>{hover.current_party ?? "Independent"}{hover.constituency ? ` · ${hover.constituency}` : ""}</span></>
            : "Hover a seat to see the member · click to open their profile"}
        </span>
      </div>

      <svg viewBox={`0 0 ${VW} ${VH}`} width="100%" role="img" aria-label={`${scope === "ls" ? "Lok Sabha" : "Rajya Sabha"} seat map`} style={{ display: "block", maxHeight: 540 }}>
        {seats.map((s, k) => {
          const m = ordered[k];
          if (!m) return null;
          const x = cx + outerR * s.rad * Math.cos(s.angle);
          const y = cy - outerR * s.rad * Math.sin(s.angle);
          const dim = activeIds.size > 0 && activeIds.size < members.length && !activeIds.has(m.id);
          return (
            <circle
              key={m.id}
              cx={x} cy={y} r={dotR}
              fill={partyColor(m.current_party)}
              style={{ stroke: "var(--bg)", strokeWidth: 0.7, opacity: dim ? 0.1 : 1, cursor: "pointer", transition: "opacity .15s" }}
              onMouseEnter={() => setHover(m)}
              onMouseLeave={() => setHover((h) => (h?.id === m.id ? null : h))}
              onClick={() => router.push(`/person/${m.id}`)}
            >
              <title>{`${m.display_name} · ${m.current_party ?? "Independent"}${m.constituency ? ` · ${m.constituency}` : ""}`}</title>
            </circle>
          );
        })}
      </svg>

      {/* legend */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: "8px 16px", marginTop: 14, paddingTop: 14, borderTop: "1px solid var(--rule)" }}>
        {legendMain.map(([name, ms]) => (
          <button
            key={name}
            type="button"
            onClick={() => router.push(`/person/${ms[0].id}`)}
            title={`${name} — ${ms.length}`}
            style={{ display: "inline-flex", alignItems: "center", gap: 7, border: "none", background: "transparent", padding: 0, cursor: "pointer", maxWidth: 260 }}
          >
            <span style={{ width: 11, height: 11, borderRadius: 3, background: partyColor(name), flexShrink: 0 }} />
            <span style={{ fontSize: 12.5, color: "var(--ink)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{name}</span>
            <span className="mono" style={{ fontSize: 12, color: "var(--muted)" }}>{ms.length}</span>
          </button>
        ))}
        {restCount > 0 && (
          <span style={{ display: "inline-flex", alignItems: "center", gap: 7 }}>
            <span style={{ width: 11, height: 11, borderRadius: 3, background: "#9AA0A6", flexShrink: 0 }} />
            <span style={{ fontSize: 12.5, color: "var(--muted)" }}>Others</span>
            <span className="mono" style={{ fontSize: 12, color: "var(--muted)" }}>{restCount}</span>
          </span>
        )}
      </div>
    </div>
  );
}
