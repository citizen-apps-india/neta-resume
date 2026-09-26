"use client";

import { useId, useState } from "react";
import type { EciSelection, EciSelectionMember, EciSelectionRegime } from "@/types/eci-files";
import { formatEciDate, formatLooseDate, officeAbbrev } from "@/lib/eci-files";

const ROW_H = 34;
const MARGIN_TOP = 20;
const LEFT_LINE_X = 190;
const RIGHT_LINE_X = 520;
const WIDTH = 720;

interface GraphNode { id: string; label: string; href: string; y: number }
interface GraphEdge { id: string; from: string; to: string; part: string; entryIds: string[]; selectionId: string; label: string }

const PART_VERB: Record<string, string> = {
  voted_with_majority: "voted with the majority", proposed: "proposed the appointment of",
  recommended: "recommended", dissented: "dissented on", convention: "the appointment of",
};

function edgeStyle(part: string): { stroke: string; width: number; dash?: string } {
  if (part === "proposed") return { stroke: "var(--eci-ink)", width: 3 };
  if (part === "voted_with_majority") return { stroke: "var(--eci-ink)", width: 1.5 };
  if (part === "recommended") return { stroke: "var(--eci-ink)", width: 1.5, dash: "2 3" };
  if (part === "dissented") return { stroke: "var(--eci-claim)", width: 1.5, dash: "2 3" };
  if (part === "convention") return { stroke: "var(--rule)", width: 1 };
  return { stroke: "var(--rule)", width: 1 };
}

function leftNodeIdFor(m: EciSelectionMember): string {
  return m.person_slug ? `person:${m.person_slug}` : `role:${m.role}`;
}

/** The bipartite selection graph on `/eci-files/selections` (PHASE4-SPEC.md §3 step 3): selectors on the
 *  left, appointments on the right, one edge per (member, appointee) pair, styled by `part`. Hidden below
 *  720px (`.eci-graph` in globals.css) — the `SelectionList`/departures table below is the accessible form
 *  at every width, and this SVG points at it via `aria-describedby`. Every edge is asserted (dev-only) to
 *  cite at least one entry, since an uncited edge in a graph like this is exactly the kind of claim that
 *  shouldn't ship quietly. */
export function SelectionGraph({ selections, regimes }: { selections: EciSelection[]; regimes: EciSelectionRegime[] }) {
  const titleId = useId();
  const [hover, setHover] = useState<string | null>(null);
  const regimeLabel = new Map<string, string>(regimes.map((r) => [r.key, r.label]));

  const asc = [...selections].sort((a, b) => (a.date < b.date ? -1 : a.date > b.date ? 1 : 0));

  const leftOrder: string[] = [];
  const leftMeta = new Map<string, { label: string; href: string }>();
  const hasConvention = asc.some((s) => s.members.length === 0 && s.method === "executive_appointment");
  if (hasConvention) {
    leftOrder.push("gov-convention");
    leftMeta.set("gov-convention", { label: "Union government (convention)", href: "/eci-files/selections#regimes" });
  }
  for (const sel of asc) {
    for (const m of sel.members) {
      if (m.person_slug) continue;
      const id = leftNodeIdFor(m);
      if (!leftMeta.has(id)) { leftOrder.push(id); leftMeta.set(id, { label: m.role, href: "/eci-files/selections#regimes" }); }
    }
  }
  for (const sel of asc) {
    for (const m of sel.members) {
      if (!m.person_slug) continue;
      const id = leftNodeIdFor(m);
      if (!leftMeta.has(id)) { leftOrder.push(id); leftMeta.set(id, { label: m.name ?? m.role, href: `/eci-files/people/${m.person_slug}` }); }
    }
  }
  const leftNodes: GraphNode[] = leftOrder.map((id, i) => ({ id, ...leftMeta.get(id)!, y: MARGIN_TOP + i * ROW_H }));

  const rightNodes: (GraphNode & { regime: string })[] = [];
  asc.forEach((sel) => {
    sel.appointed.forEach((a) => {
      rightNodes.push({
        id: `${sel.id}:${a.person_slug}`,
        label: `${a.name} · ${officeAbbrev(a.office)} · ${formatLooseDate(sel.date)}`,
        href: `/eci-files/people/${a.person_slug}`,
        y: MARGIN_TOP + rightNodes.length * ROW_H,
        regime: sel.regime,
      });
    });
  });

  const edges: GraphEdge[] = [];
  asc.forEach((sel) => {
    const appointeeIds = sel.appointed.map((a) => `${sel.id}:${a.person_slug}`);
    if (sel.members.length === 0) {
      appointeeIds.forEach((to) => {
        edges.push({ id: `${sel.id}-gov-${to}`, from: "gov-convention", to, part: "convention", entryIds: sel.entry_ids, selectionId: sel.id, label: `appointed · selection of ${formatEciDate(sel.date, sel.date_precision)}` });
      });
    } else {
      sel.members.forEach((m) => {
        const from = leftNodeIdFor(m);
        appointeeIds.forEach((to) => {
          const verb = PART_VERB[m.part] ?? m.part;
          edges.push({
            id: `${sel.id}-${from}-${to}`, from, to, part: m.part, entryIds: m.entry_ids, selectionId: sel.id,
            label: `${m.name ?? m.role} ${verb} · selection of ${formatEciDate(sel.date, sel.date_precision)}${m.entry_ids[0] ? ` · cites ${m.entry_ids[0]}` : ""}`,
          });
        });
      });
    }
  });

  if (process.env.NODE_ENV !== "production") {
    for (const e of edges) if (e.entryIds.length === 0) console.error(`SelectionGraph: edge ${e.id} cites no entry`);
  }

  const byId = new Map<string, GraphNode>([...leftNodes, ...rightNodes].map((n) => [n.id, n]));
  const height = MARGIN_TOP * 2 + Math.max(leftNodes.length, rightNodes.length) * ROW_H;

  const bands: { y0: number; y1: number; regime: string }[] = [];
  rightNodes.forEach((n) => {
    const prev = bands[bands.length - 1];
    if (prev && prev.regime === n.regime) prev.y1 = n.y + ROW_H / 2;
    else bands.push({ y0: n.y - ROW_H / 2, y1: n.y + ROW_H / 2, regime: n.regime });
  });

  return (
    <div className="eci-graph" data-focus={hover ? "true" : undefined}>
      <svg
        width="100%" viewBox={`0 0 ${WIDTH} ${height}`} role="img" aria-labelledby={titleId} aria-describedby="selection-list"
        onMouseLeave={() => setHover(null)}
      >
        <title id={titleId}>{selections.length} selections, {leftNodes.length} selectors and {rightNodes.length} appointments, 2019 to today</title>

        {bands.map((b, i) => (
          <g key={i}>
            <rect x={RIGHT_LINE_X - 4} y={b.y0} width={WIDTH - RIGHT_LINE_X + 4} height={b.y1 - b.y0} fill="color-mix(in srgb, var(--eci-ink) 5%, transparent)" />
            <text x={WIDTH - 4} y={b.y0 + 12} textAnchor="end" fontSize={9.5} fill="var(--faint)">{regimeLabel.get(b.regime) ?? b.regime}</text>
          </g>
        ))}

        {edges.map((e) => {
          const from = byId.get(e.from);
          const to = byId.get(e.to);
          if (!from || !to) return null;
          const style = edgeStyle(e.part);
          const midX = (LEFT_LINE_X + RIGHT_LINE_X) / 2;
          const midY = (from.y + to.y) / 2;
          return (
            <g key={e.id} className="eci-edge" data-on={hover && (e.from === hover || e.to === hover) ? "true" : undefined}>
              <a href={`#${e.selectionId}`}>
                <path
                  d={`M${LEFT_LINE_X},${from.y} C${midX},${from.y} ${midX},${to.y} ${RIGHT_LINE_X},${to.y}`}
                  fill="none" stroke={style.stroke} strokeWidth={style.width} strokeDasharray={style.dash}
                />
                <path
                  className="eci-edge-hit"
                  d={`M${LEFT_LINE_X},${from.y} C${midX},${from.y} ${midX},${to.y} ${RIGHT_LINE_X},${to.y}`}
                  fill="none" stroke="transparent" strokeWidth={12}
                >
                  <title>{e.label}</title>
                </path>
                {e.part === "dissented" && (
                  <text x={midX} y={midY + 4} textAnchor="middle" fontSize={11} fill="var(--eci-claim)">×</text>
                )}
              </a>
            </g>
          );
        })}

        {leftNodes.map((n) => (
          <a key={n.id} href={n.href} className="eci-node" onMouseEnter={() => setHover(n.id)} onFocus={() => setHover(n.id)} onBlur={() => setHover(null)}>
            <text x={LEFT_LINE_X - 10} y={n.y + 4} textAnchor="end" fontSize={12} fill="var(--ink)">{n.label}</text>
            <circle cx={LEFT_LINE_X} cy={n.y} r={3} fill="var(--ink2)" />
          </a>
        ))}

        {rightNodes.map((n) => (
          <a key={n.id} href={n.href} className="eci-node" onMouseEnter={() => setHover(n.id)} onFocus={() => setHover(n.id)} onBlur={() => setHover(null)}>
            <circle cx={RIGHT_LINE_X} cy={n.y} r={3} fill="var(--eci-ink)" />
            <text x={RIGHT_LINE_X + 10} y={n.y + 4} textAnchor="start" fontSize={12} fill="var(--ink)">{n.label}</text>
          </a>
        ))}
      </svg>
    </div>
  );
}
