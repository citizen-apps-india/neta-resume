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
      className="mono"
      style={{ textAlign: "center", fontSize: 12, color: "var(--muted)", padding: "18px 16px 0", letterSpacing: "0.02em" }}
    >
      <span style={{ color: "var(--accent)" }}>●</span>{" "}
      <strong style={{ color: "var(--ink2)", fontWeight: 600 }}>{count.toLocaleString("en-IN")}</strong>{" "}
      citizens have looked up their representatives
    </div>
  );
}
