// Provenance badge — renders next to every fact so users can click through to the source.
// This component is the visual enforcement of the "no fact without a source" invariant.

import type { Source } from "@/lib/api";

const TIER_LABEL: Record<number, string> = {
  1: "official",
  2: "ADR/TCPD",
  3: "reported",
};

export function SourceBadge({ source }: { source: Source | null }) {
  if (!source) return null;
  const tier = TIER_LABEL[source.trust_tier] ?? "source";
  const label = `${source.name} · ${tier}`;
  return source.url ? (
    <a
      href={source.url}
      target="_blank"
      rel="noopener noreferrer"
      title={`Source: ${label}`}
      style={{ fontSize: "0.7rem", color: "#666", marginLeft: 6, textDecoration: "underline" }}
    >
      [source]
    </a>
  ) : (
    <span title={`Source: ${label}`} style={{ fontSize: "0.7rem", color: "#999", marginLeft: 6 }}>
      [{tier}]
    </span>
  );
}
