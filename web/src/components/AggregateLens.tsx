import { SegmentedBar } from "@/components/resume/policy-focus";
import { THEME_COLORS } from "@/lib/themes";
import type { AggregateGroup, ThemeShare } from "@/lib/api";

// Canonical theme order (shared with the dashboard donut) so every group's share-bar lays its themes out
// left-to-right the same way — the colours line up and groups become visually comparable.
const ORDER = Object.keys(THEME_COLORS);
const rank = (t: string) => { const i = ORDER.indexOf(t); return i === -1 ? ORDER.length : i; };
const canonical = (themes: ThemeShare[]) =>
  [...themes].sort((a, b) => rank(a.theme) - rank(b.theme)).map((t) => ({ theme: t.theme, count: t.count, share: t.share }));

const fmt = (n: number) => n.toLocaleString("en-IN");

function GroupRow({ g, highlighted }: { g: AggregateGroup; highlighted?: boolean }) {
  const top = [...g.themes].sort((a, b) => b.share - a.share)[0];
  return (
    <div style={{
      padding: "13px 14px", borderRadius: 10,
      border: `1px solid ${highlighted ? "var(--accent)" : "var(--rule)"}`,
      background: highlighted ? "var(--accent-soft)" : "var(--card2)",
    }}>
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 12, marginBottom: 9 }}>
        <span style={{ fontFamily: "'Bricolage Grotesque',sans-serif", fontSize: 14.5, fontWeight: 600, color: "var(--ink)" }}>{g.key}</span>
        <span className="mono" style={{ fontSize: 11.5, color: "var(--muted)", flexShrink: 0 }}>{fmt(g.total)} Qs · {fmt(g.mps)} MPs</span>
      </div>
      <SegmentedBar focus={canonical(g.themes)} />
      {top && (
        <div style={{ fontSize: 11.5, color: "var(--muted)", marginTop: 8 }}>
          Most on <strong style={{ color: "var(--ink2)", fontWeight: 600 }}>{top.theme}</strong> — {Math.round(top.share * 100)}% of its questions
        </div>
      )}
    </div>
  );
}

/** Ranked party/state list, each as a policy-theme SHARE bar (descriptive emphasis, not a ranking of merit).
 *  When `focus` matches a group it's pinned to the top and highlighted (used from a member's profile). */
export function AggregateLens({ groups, kind, focus }: { groups: AggregateGroup[]; kind: "party" | "state"; focus?: string }) {
  const pinned = focus ? groups.find((g) => g.key === focus) : undefined;
  const rest = pinned ? groups.filter((g) => g.key !== pinned.key) : groups;

  return (
    <div>
      {/* Theme legend, once */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: "6px 14px", marginBottom: 18 }}>
        {ORDER.map((t) => (
          <span key={t} style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: 11.5, color: "var(--ink2)" }}>
            <span style={{ width: 10, height: 10, borderRadius: 3, background: THEME_COLORS[t] }} />{t}
          </span>
        ))}
      </div>

      {pinned && (
        <div style={{ marginBottom: 18 }}>
          <div className="mono" style={{ fontSize: 10.5, letterSpacing: "0.06em", color: "var(--accent)", marginBottom: 7 }}>FROM THIS PROFILE</div>
          <GroupRow g={pinned} highlighted />
        </div>
      )}

      <div style={{ display: "grid", gap: 10 }}>
        {rest.map((g) => <GroupRow key={g.key} g={g} />)}
      </div>

      <p style={{ fontSize: 12, color: "var(--muted)", margin: "18px 0 0", maxWidth: "72ch" }}>
        Bars show each {kind}&rsquo;s <strong>share of emphasis</strong> across policy themes — what its members
        collectively raise, derived from the official ministry each question addressed. This describes focus,
        not merit or effort; a larger {kind} isn&rsquo;t &ldquo;more&rdquo; because share is normalised. Missing ≠ zero.
      </p>
    </div>
  );
}
