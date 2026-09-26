import Link from "next/link";
import type { EciAnswersCounts } from "@/types/eci-files";
import type { EciAnswersView2 } from "@/lib/eci-files";

const BASE_PATH = "/eci-files/answers";

/** The four filter pills above the charge-and-answer list: total, answered, unanswered, and "with a
 *  document" (a primary record entry bears directly on the point). "With a response" and "With a
 *  document" are both already counted server-side (`EciAnswersCounts`); the page filters the fetched rows
 *  by them locally rather than adding a fifth API view. */
export function AnswerFilterChips({ view, counts }: { view: EciAnswersView2; counts: EciAnswersCounts }) {
  const chips: { view: EciAnswersView2; label: string; count: number }[] = [
    { view: "all", label: "All", count: counts.rows },
    { view: "with-response", label: "With a response", count: counts.with_response },
    { view: "no-response", label: "No response on record", count: counts.without_response },
    { view: "with-record", label: "With a document", count: counts.with_record },
  ];
  return (
    <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 20 }}>
      {chips.map((c) => {
        const active = view === c.view;
        return (
          <Link
            key={c.view}
            href={c.view === "all" ? BASE_PATH : `${BASE_PATH}?view=${c.view}`}
            aria-current={active ? "page" : undefined}
            className="tap"
            style={{
              display: "inline-flex", alignItems: "center", gap: 7, fontSize: 13, padding: "0 14px", minHeight: 38,
              borderRadius: 999, textDecoration: "none",
              border: `1px solid ${active ? "var(--ink)" : "var(--border)"}`,
              background: active ? "var(--ink)" : "var(--card)",
              color: active ? "var(--bg)" : "var(--ink)",
            }}
          >
            {c.label}
            <span className="mono" style={{ fontSize: 11.5, color: active ? "var(--bg)" : "var(--muted)", opacity: active ? 0.75 : 1 }}>
              {c.count}
            </span>
          </Link>
        );
      })}
    </div>
  );
}
