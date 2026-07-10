"use client";

// Recharts-backed charts: interactive, responsive, and dark-mode aware. Same prop shapes as before
// (Donut/WealthLine) so call sites are untouched.

import {
  Area, AreaChart, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { rupees } from "@/lib/format";
import { themeColor } from "@/lib/themes";
import { resolveColor, useThemeColors } from "@/lib/useThemeColors";

export interface DonutSeg {
  label: string;
  value: number;
  color: string;
}

function TooltipBox({ children }: { children: React.ReactNode }) {
  return (
    <div
      className="mono"
      style={{
        background: "var(--card)", border: "1px solid var(--border)", borderRadius: 8,
        padding: "7px 10px", fontSize: 12, color: "var(--ink)", boxShadow: "0 8px 24px -12px rgba(0,0,0,0.4)",
      }}
    >
      {children}
    </div>
  );
}

/** Severity / distribution donut with a centred count + legend. */
export function Donut({
  segments,
  centerNum,
  centerLabel,
  size = 140,
}: {
  segments: DonutSeg[];
  centerNum: string | number;
  centerLabel: string;
  size?: number;
}) {
  const colors = useThemeColors();
  const data = segments.filter((s) => s.value > 0);

  // Fit the centre number into the donut hole (long values like "4568.22 Cr" must not overflow).
  const innerD = size * 0.58;
  const numStr = String(centerNum).trim();
  const [mainTok, ...rest] = numStr.split(/\s+/);
  const unitTok = rest.join(" ");
  const weightedLen = mainTok.length + (unitTok ? unitTok.length * 0.55 + 0.6 : 0);
  const mainSize = Math.max(13, Math.min(26, (innerD * 0.86) / (Math.max(weightedLen, 1) * 0.62)));
  const unitSize = Math.max(9, mainSize * 0.55);

  return (
    <div className="nr-donut">
      <div style={{ position: "relative", width: size, height: size, flexShrink: 0 }}>
        <PieChart width={size} height={size}>
          <Pie
            data={data}
            dataKey="value"
            nameKey="label"
            cx="50%"
            cy="50%"
            innerRadius={size * 0.33}
            outerRadius={size * 0.48}
            startAngle={90}
            endAngle={-270}
            paddingAngle={data.length > 1 ? 2 : 0}
            stroke="none"
            isAnimationActive
          >
            {data.map((s) => (
              <Cell key={s.label} fill={resolveColor(colors, s.color)} />
            ))}
          </Pie>
          <Tooltip
            content={({ active, payload }) =>
              active && payload && payload.length ? (
                <TooltipBox>
                  {payload[0].name}: <strong>{payload[0].value}</strong>
                </TooltipBox>
              ) : null
            }
          />
        </PieChart>
        <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: "0 4px", pointerEvents: "none" }}>
          <div style={{ display: "flex", alignItems: "baseline", gap: 3, maxWidth: innerD, lineHeight: 1, whiteSpace: "nowrap" }}>
            <span className="mono" style={{ fontSize: mainSize, fontWeight: 600 }}>{mainTok}</span>
            {unitTok && <span className="mono" style={{ fontSize: unitSize, fontWeight: 600, color: "var(--muted)" }}>{unitTok}</span>}
          </div>
          <div style={{ fontSize: 9.5, color: "var(--muted)", marginTop: 3, whiteSpace: "nowrap" }}>{centerLabel}</div>
        </div>
      </div>
      <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 9 }}>
        {segments.map((s) => (
          <div key={s.label} style={{ display: "flex", alignItems: "center", gap: 9 }}>
            <span style={{ width: 10, height: 10, borderRadius: 3, background: s.color, flexShrink: 0 }} />
            <span style={{ fontSize: 12, color: "var(--ink2)", flex: 1, lineHeight: 1.1 }}>{s.label}</span>
            <span className="mono" style={{ fontSize: 13, fontWeight: 600, color: s.color }}>{s.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

/** Net-assets-by-cycle area+line. Degrades to a single marker when only one cycle exists. */
export function WealthLine({ points }: { points: { label: string; value: number }[] }) {
  const colors = useThemeColors();
  const accent = colors["--accent"];
  const gid = "wealthFill";

  return (
    <div style={{ width: "100%", height: "clamp(140px,42vw,168px)" }}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={points} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
          <defs>
            <linearGradient id={gid} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={accent} stopOpacity={0.22} />
              <stop offset="100%" stopColor={accent} stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <XAxis
            dataKey="label"
            tick={{ fontSize: 10.5, fill: colors["--muted"], fontFamily: "var(--font-mono, monospace)" }}
            tickLine={false}
            axisLine={{ stroke: colors["--rule2"] }}
            interval="preserveStartEnd"
            minTickGap={12}
          />
          <YAxis hide domain={[0, "dataMax"]} />
          <Tooltip
            cursor={{ stroke: colors["--rule2"] }}
            content={({ active, payload, label }) =>
              active && payload && payload.length ? (
                <TooltipBox>
                  <div style={{ color: "var(--muted)", marginBottom: 2 }}>{label}</div>
                  <strong>{rupees(payload[0].value as number)}</strong>
                </TooltipBox>
              ) : null
            }
          />
          <Area
            type="monotone"
            dataKey="value"
            stroke={accent}
            strokeWidth={2.5}
            fill={`url(#${gid})`}
            dot={{ r: 3.5, fill: colors["--card"], stroke: accent, strokeWidth: 2.5 }}
            activeDot={{ r: 5, fill: accent, stroke: colors["--card"], strokeWidth: 2 }}
            isAnimationActive
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

/** "YYYY-MM" -> "Jul '24" for compact month ticks. */
function monthLabel(ym: string): string {
  const [y, m] = ym.split("-").map(Number);
  const name = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][(m || 1) - 1];
  return `${name} '${String(y).slice(2)}`;
}

/** Monthly question volume stacked by policy theme — how the House's attention shifted over the term.
 *  Each theme is one stacked <Area>, coloured by the shared theme palette; months are pre-densified by the
 *  API so the stack is continuous across sittings. Rendered under /parliament/trends. */
export function ThemeStackedArea({ months, series }: { months: string[]; series: { theme: string; points: number[] }[] }) {
  const colors = useThemeColors();
  const fill = (t: string) => resolveColor(colors, themeColor(t));
  const data = months.map((m, i) => {
    const row: Record<string, string | number> = { month: monthLabel(m) };
    for (const s of series) row[s.theme] = s.points[i] ?? 0;
    return row;
  });

  return (
    <>
      <div style={{ width: "100%", height: "clamp(200px,44vw,360px)" }}>
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
            <XAxis
              dataKey="month"
              tick={{ fontSize: 10.5, fill: colors["--muted"], fontFamily: "var(--font-mono, monospace)" }}
              tickLine={false}
              axisLine={{ stroke: colors["--rule2"] }}
              interval="preserveStartEnd"
              minTickGap={20}
            />
            <YAxis
              tick={{ fontSize: 10.5, fill: colors["--muted"], fontFamily: "var(--font-mono, monospace)" }}
              tickLine={false}
              axisLine={false}
              width={34}
            />
            <Tooltip
              cursor={{ stroke: colors["--rule2"] }}
              content={({ active, payload, label }) => {
                if (!active || !payload || !payload.length) return null;
                const rows = [...payload].filter((p) => (p.value as number) > 0).reverse();
                const total = payload.reduce((n, p) => n + (p.value as number), 0);
                return (
                  <TooltipBox>
                    <div style={{ color: "var(--muted)", marginBottom: 4 }}>{label} · <strong style={{ color: "var(--ink)" }}>{total.toLocaleString("en-IN")}</strong> questions</div>
                    {rows.map((p) => (
                      <div key={p.dataKey as string} style={{ display: "flex", alignItems: "center", gap: 6, lineHeight: 1.5 }}>
                        <span style={{ width: 8, height: 8, borderRadius: 2, background: p.color as string }} />
                        <span style={{ color: "var(--ink2)", flex: 1 }}>{p.dataKey as string}</span>
                        <strong>{(p.value as number).toLocaleString("en-IN")}</strong>
                      </div>
                    ))}
                  </TooltipBox>
                );
              }}
            />
            {series.map((s) => (
              <Area
                key={s.theme}
                type="monotone"
                dataKey={s.theme}
                stackId="1"
                stroke={fill(s.theme)}
                strokeWidth={0.75}
                fill={fill(s.theme)}
                fillOpacity={0.82}
                isAnimationActive={false}
              />
            ))}
          </AreaChart>
        </ResponsiveContainer>
      </div>
      <div style={{ display: "flex", flexWrap: "wrap", gap: "6px 14px", marginTop: 14 }}>
        {series.map((s) => (
          <span key={s.theme} style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: 11.5, color: "var(--ink2)" }}>
            <span style={{ width: 10, height: 10, borderRadius: 3, background: themeColor(s.theme) }} />
            {s.theme}
          </span>
        ))}
      </div>
    </>
  );
}
