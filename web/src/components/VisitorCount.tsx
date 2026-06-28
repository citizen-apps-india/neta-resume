import { headers } from "next/headers";
import { bumpVisits, getVisits } from "@/lib/api";

/** Homepage lifetime unique-visitor caption. Increments once per new browser (flagged by middleware). */
export async function VisitorCount() {
  let count = 0;
  try {
    const isNew = (await headers()).get("x-nr-new") === "1";
    const r = isNew ? await bumpVisits() : await getVisits();
    count = r.count;
  } catch {
    return null; // API down — show nothing rather than a broken stat
  }
  if (!count) return null;

  return (
    <div
      className="fadeUp"
      style={{
        display: "inline-flex", alignItems: "center", gap: 9, padding: "7px 14px", borderRadius: 999,
        border: "1px solid var(--border)", background: "var(--card2)", fontSize: 12.5, color: "var(--muted)",
      }}
    >
      <span style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--ok)", animation: "nrPulse 2s infinite", flexShrink: 0 }} />
      <span>
        <strong className="mono" style={{ color: "var(--ink)", fontWeight: 600 }}>{count.toLocaleString("en-IN")}</strong>{" "}
        citizens have looked up their leaders
      </span>
    </div>
  );
}
