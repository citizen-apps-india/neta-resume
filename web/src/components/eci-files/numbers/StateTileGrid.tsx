"use client";

import { useRef, useState } from "react";
import Link from "next/link";
import type { EciTileViewModel } from "@/lib/eci-numbers";

type Dir = "up" | "down" | "left" | "right" | "home" | "end";
const KEY_TO_DIR: Record<string, Dir> = { ArrowUp: "up", ArrowDown: "down", ArrowLeft: "left", ArrowRight: "right", Home: "home", End: "end" };

/** The equal-size, geography-shaped tile grid (never a map — PHASE3-SPEC.md §"Decisions"). Every tile is
 *  a real `<Link>` (works with no JS); this component only adds the roving-tabindex keyboard nav on top.
 *  Takes plain view models, not `EciRegionSummary`/`EciMetricDef` — the metric's `encode`/`missingReason`
 *  functions can't cross the server/client boundary as props, so `lib/eci-numbers.ts#buildTileViewModels`
 *  resolves everything server-side first. */
export function StateTileGrid({ tiles, groupLabel }: { tiles: EciTileViewModel[]; groupLabel: string }) {
  const [active, setActive] = useState<string | undefined>(tiles[0]?.slug);
  const [readout, setReadout] = useState<string | null>(null);
  const gridRef = useRef<HTMLDivElement>(null);
  const bySlug = new Map(tiles.map((t) => [t.slug, t]));

  function focusTile(slug: string) {
    setActive(slug);
    requestAnimationFrame(() => {
      gridRef.current?.querySelector<HTMLAnchorElement>(`[data-slug="${slug}"]`)?.focus();
    });
  }

  function moveFocus(fromSlug: string, dir: Dir) {
    const from = bySlug.get(fromSlug);
    if (!from) return;

    if (dir === "home" || dir === "end") {
      const rowItems = tiles.filter((t) => t.row === from.row);
      const target = dir === "home" ? rowItems[0] : rowItems[rowItems.length - 1];
      if (target) focusTile(target.slug);
      return;
    }

    const axis = dir === "left" || dir === "right" ? "col" : "row";
    const sign = dir === "left" || dir === "up" ? -1 : 1;
    let best: { slug: string; primary: number; secondary: number } | null = null;
    for (const t of tiles) {
      if (t.slug === fromSlug) continue;
      const delta = axis === "col" ? t.col - from.col : t.row - from.row;
      if (delta === 0 || Math.sign(delta) !== sign) continue;
      const perpDelta = Math.abs(axis === "col" ? t.row - from.row : t.col - from.col);
      const primary = Math.abs(delta);
      if (!best || primary < best.primary || (primary === best.primary && perpDelta < best.secondary)) {
        best = { slug: t.slug, primary, secondary: perpDelta };
      }
    }
    if (best) focusTile(best.slug);
  }

  function onKeyDown(e: React.KeyboardEvent, slug: string) {
    const dir = KEY_TO_DIR[e.key];
    if (!dir) return;
    e.preventDefault();
    moveFocus(slug, dir);
  }

  return (
    <div>
      <div ref={gridRef} role="group" aria-label={`States and union territories, coloured by ${groupLabel}`} className="eci-tiles">
        {tiles.map((tile) => {
          const modifier =
            tile.kind === "value" ? "" :
            tile.kind === "no_measure" ? "eci-tile--nomeasure" :
            tile.kind === "other_exercise" ? "eci-tile--other" : "eci-tile--empty";

          return (
            <Link
              key={tile.slug}
              href={`/eci-files/numbers/${tile.slug}`}
              data-slug={tile.slug}
              data-band={tile.band}
              className={`eci-tile${modifier ? ` ${modifier}` : ""}`}
              style={{ gridRow: tile.row + 1, gridColumn: tile.col + 1 }}
              tabIndex={active === tile.slug ? 0 : -1}
              aria-label={tile.ariaLabel}
              onKeyDown={(e) => onKeyDown(e, tile.slug)}
              onFocus={() => { setActive(tile.slug); setReadout(tile.readout); }}
              onMouseEnter={() => setReadout(tile.readout)}
              onMouseLeave={() => setReadout(null)}
            >
              <span className="mono eci-tile-code">{tile.code}</span>
              {tile.valueText && <span className="eci-tile-value">{tile.valueText}</span>}
              {tile.subText && <span className="eci-tile-sub">{tile.subText}</span>}
            </Link>
          );
        })}
      </div>
      <p aria-hidden className="mono" style={{ fontSize: 11.5, color: "var(--muted)", marginTop: 10 }}>
        {readout ?? "Hover or focus a tile; open it for the state's full journey."}
      </p>
    </div>
  );
}
