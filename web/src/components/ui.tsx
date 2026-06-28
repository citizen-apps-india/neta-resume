// Design-system primitives (server components). Styling mirrors the Neta-Resume Design System:
// every fact wears its source; party identity only ever shows as a pill; severity uses sev tokens.

import type { ReactNode } from "react";
import type { Source } from "@/lib/api";
import { severityMeta, type Severity } from "@/lib/format";

/** Provenance chip — "↗ ECI AFFIDAVIT". A fact without a citation does not ship. */
export function SourceChip({ source, label }: { source: Source | null; label?: string }) {
  if (!source) return null;
  const text = label ?? `${source.name}`;
  const inner = (
    <span
      className="mono"
      style={{
        display: "inline-flex", alignItems: "center", gap: 6, fontSize: 10.5,
        padding: "5px 10px", borderRadius: 6, border: "1px solid var(--accent-soft-bd)",
        background: "var(--accent-soft)", color: "var(--accent-soft-fg)", whiteSpace: "nowrap",
      }}
    >
      ↗ {text}
    </span>
  );
  return source.url ? (
    <a href={source.url} target="_blank" rel="noopener noreferrer" style={{ textDecoration: "none" }}>
      {inner}
    </a>
  ) : inner;
}

/** Small inline source link used in dense rows. */
export function SourceLink({ source }: { source: Source | null }) {
  if (!source) return null;
  const txt = (
    <span className="mono" style={{ fontSize: 10, color: "var(--accent)" }}>
      ↗ {source.name}
    </span>
  );
  return source.url ? (
    <a href={source.url} target="_blank" rel="noopener noreferrer" style={{ textDecoration: "none" }}>{txt}</a>
  ) : txt;
}

export function SeverityBadge({ severity, total }: { severity: Severity; total?: number }) {
  if (total === 0) {
    return (
      <span className="mono" style={chip("var(--ok-bg)", "var(--ok)")}>
        <Dot color="var(--ok)" sq /> NO CASES
      </span>
    );
  }
  const m = severityMeta(severity);
  return (
    <span className="mono" style={chip(m.bg, m.fg)}>
      <Dot color={m.fg} sq /> {m.label}
    </span>
  );
}

export function PendingFlag({ children = "PENDING · UNPROVEN" }: { children?: ReactNode }) {
  return (
    <span
      className="mono"
      style={{
        display: "inline-flex", alignItems: "center", fontSize: 10.5, fontWeight: 500,
        padding: "5px 11px", borderRadius: 6, background: "var(--sunken)", color: "var(--muted)",
        border: "1px dashed var(--border2)", letterSpacing: "0.02em",
      }}
    >
      {children}
    </span>
  );
}

export function PartyPill({ party, current = true }: { party: string | null; current?: boolean }) {
  if (!party) return null;
  return (
    <span
      style={{
        display: "inline-flex", alignItems: "center", gap: 7, fontSize: 12, fontWeight: current ? 600 : 500,
        padding: "5px 11px", borderRadius: 20, border: "1px solid var(--border)",
        background: current ? "var(--card2)" : "var(--sunken)", color: current ? "var(--ink)" : "var(--muted)",
        maxWidth: "100%", whiteSpace: "nowrap",
      }}
    >
      <span style={{ width: 9, height: 9, borderRadius: "50%", background: current ? "var(--accent-2)" : "var(--faint)", flexShrink: 0 }} />
      <span style={{ overflow: "hidden", textOverflow: "ellipsis" }}>{party}</span>
    </span>
  );
}

export function Dot({ color, sq = false }: { color: string; sq?: boolean }) {
  return <span style={{ width: 7, height: 7, borderRadius: sq ? 2 : "50%", background: color, flexShrink: 0 }} />;
}

/** Official photo when available (sansad.in), else a hatched placeholder. */
export function PhotoBox({ w = 60, h = 72, label, src }: { w?: number; h?: number; label?: string; src?: string | null }) {
  if (src) {
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img
        src={src}
        alt=""
        width={w}
        height={h}
        loading="lazy"
        style={{ width: w, height: h, borderRadius: 8, flexShrink: 0, objectFit: "cover", border: "1px solid var(--rule)", background: "var(--photo-b)" }}
      />
    );
  }
  return (
    <div
      style={{
        width: w, height: h, borderRadius: 8, flexShrink: 0, border: "1px solid var(--rule)",
        background: "repeating-linear-gradient(135deg,var(--photo-a),var(--photo-a) 6px,var(--photo-b) 6px,var(--photo-b) 12px)",
        display: "flex", alignItems: "flex-end", justifyContent: "center", paddingBottom: 5,
      }}
    >
      {label && <span className="mono" style={{ fontSize: 7.5, color: "var(--faint)" }}>{label}</span>}
    </div>
  );
}

/** Browser-chrome frame used to present full screens. */
export function Frame({ url, children }: { url: string; children: ReactNode }) {
  return (
    <div style={{ border: "1px solid var(--border)", borderRadius: 14, overflow: "hidden", boxShadow: "0 24px 60px -28px var(--shadow)", background: "var(--bg)" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "12px 16px", background: "var(--panel)", borderBottom: "1px solid var(--rule)" }}>
        {[0, 1, 2].map((i) => (
          <span key={i} style={{ width: 11, height: 11, borderRadius: "50%", background: "var(--border)" }} />
        ))}
        <div className="mono" style={{ marginLeft: 14, flex: 1, maxWidth: 420, minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", background: "var(--bg)", border: "1px solid var(--border)", borderRadius: 6, padding: "5px 12px", fontSize: 10.5, color: "var(--muted)" }}>
          {url}
        </div>
      </div>
      {children}
    </div>
  );
}

export function Card({ children, style }: { children: ReactNode; style?: React.CSSProperties }) {
  return (
    <div style={{ border: "1px solid var(--rule)", borderRadius: 12, background: "var(--card2)", padding: "clamp(16px,4vw,24px)", ...style }}>
      {children}
    </div>
  );
}

export function SectionLabel({ children }: { children: ReactNode }) {
  return (
    <div className="mono" style={{ fontSize: 11, letterSpacing: "0.14em", textTransform: "uppercase", color: "var(--faint)" }}>
      {children}
    </div>
  );
}

function chip(bg: string, fg: string): React.CSSProperties {
  return {
    display: "inline-flex", alignItems: "center", gap: 6, fontSize: 11, fontWeight: 500,
    padding: "5px 10px", borderRadius: 6, background: bg, color: fg, whiteSpace: "nowrap",
  };
}
