/** A `<details>` disclosure holding the current metric's method note and the shared footnote
 *  (PHASE3-SPEC.md §3.1/§3.3) — every chart on this section carries one. */
export function HowWeCounted({ text, footnote }: { text: string; footnote?: string }) {
  return (
    <details style={{ marginTop: 6, marginBottom: 24 }}>
      <summary className="mono" style={{ fontSize: 11.5, color: "var(--accent-2)", cursor: "pointer" }}>
        How we counted this
      </summary>
      <div style={{ fontSize: 12.5, color: "var(--ink2)", lineHeight: 1.55, marginTop: 8, maxWidth: "70ch" }}>
        <p style={{ margin: "0 0 8px" }}>{text}</p>
        {footnote && <p className="mono" style={{ fontSize: 11, color: "var(--muted)", margin: 0 }}>{footnote}</p>}
      </div>
    </details>
  );
}
