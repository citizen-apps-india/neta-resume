import Link from "next/link";
import type { ReactNode } from "react";

export interface FrontTile {
  href: string;
  count: number | null;
  unit: string;
  title: string;
  color: string;
  icon: ReactNode;
}

function Tile({ tile }: { tile: FrontTile }) {
  return (
    <Link
      href={tile.href}
      className="lift tap"
      style={{
        display: "flex", flexDirection: "column", gap: 12, padding: "18px 16px 16px", minHeight: 158,
        background: "var(--card)", border: "1px solid var(--rule)", borderRadius: 14, textDecoration: "none", color: "var(--ink)",
      }}
    >
      <span
        aria-hidden
        style={{
          width: 40, height: 40, borderRadius: 10, display: "inline-flex", alignItems: "center", justifyContent: "center",
          color: tile.color, background: `color-mix(in srgb, ${tile.color} 12%, transparent)`,
        }}
      >
        {tile.icon}
      </span>
      <div style={{ display: "flex", alignItems: "baseline", gap: 6 }}>
        <span className="mono" style={{ fontSize: 28, fontWeight: 700 }}>{tile.count ?? "—"}</span>
        <span style={{ fontSize: 12.5, color: "var(--muted)" }}>{tile.unit}</span>
      </div>
      <span style={{ fontSize: 14, fontWeight: 600, lineHeight: 1.3 }}>{tile.title}</span>
      <span className="mono" style={{ marginTop: "auto", fontSize: 12.5, color: "var(--ink2)", fontWeight: 600 }}>Open →</span>
    </Link>
  );
}

/** "Start here": seven doorways into the record, each with its own real count (REDESIGN brief: "seven
 *  section tiles with REAL counts fetched from the API"). Colour follows the lane the section reads
 *  closest to — Objections is the Inside-the-Commission lane, Answers is Claims, Courts is Courts — so
 *  the same five hues from the timeline carry over here instead of a sixth invented palette. */
export function FrontSectionTiles({ tiles }: { tiles: FrontTile[] }) {
  return (
    <section>
      <h2 className="mono" style={{ fontSize: 11, letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--faint)", margin: "0 0 12px" }}>
        Start here
      </h2>
      <div className="eci-front-tiles">
        {tiles.map((t) => <Tile key={t.href} tile={t} />)}
      </div>
    </section>
  );
}
