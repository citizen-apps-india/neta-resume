import { Fragment, type ReactNode } from "react";
import type { EciRuleDiff } from "@/types/eci-files";
import { diffLines, type EciDiffOp, type EciDiffSegment } from "@/lib/eci-diff";
import { TextStatusBadge } from "@/components/eci-files/views/TextStatusBadge";

const SR_ONLY: React.CSSProperties = { position: "absolute", width: 1, height: 1, overflow: "hidden", clip: "rect(0 0 0 0)" };

/** Renders one line's text, honouring its text-status: quoted lines get “ ” quotes and `.eci-diff-quoted`;
 *  on a non-verbatim side, every *other* line goes italic, so a paraphrase never reads like a quotation
 *  (PHASE5-SPEC §6.4). `segments` (word-level diff) render as `<del>`/`<ins>` where changed; plain text
 *  renders as-is. */
function LineContent({
  text, segments, mark, quoted, italic,
}: {
  text?: string;
  segments?: EciDiffSegment[];
  mark?: "del" | "ins";
  quoted: boolean;
  italic: boolean;
}) {
  const inner: ReactNode = segments
    ? segments.map((s, i) =>
        s.changed
          ? mark === "del"
            ? <del key={i}>{s.text}</del>
            : <ins key={i}>{s.text}</ins>
          : <span key={i}>{s.text}</span>,
      )
    : text;
  const body = italic ? <em>{inner}</em> : <>{inner}</>;
  // A visually hidden prefix per line: the quote marks/italics that carry "quoted" vs "paraphrased"
  // for sighted readers are otherwise silent to a screen reader.
  const srPrefix = quoted ? "Quoted in reporting: " : italic ? "Paraphrase: " : null;
  const withPrefix = (
    <>
      {srPrefix && <span style={SR_ONLY}>{srPrefix}</span>}
      {body}
    </>
  );
  return quoted ? <span className="eci-diff-quoted">&ldquo;{withPrefix}&rdquo;</span> : withPrefix;
}

interface Row {
  key: string;
  kind: "same" | "del" | "add" | "change";
  beforeNo: number | null;
  afterNo: number | null;
  before: ReactNode | null;
  after: ReactNode | null;
}

function buildRows(diff: EciRuleDiff): Row[] {
  const ops = diffLines(diff.before, diff.after);
  const quotedBefore = new Set(diff.quoted_lines_before);
  const quotedAfter = new Set(diff.quoted_lines_after);
  const italicBefore = diff.before_status !== "verbatim";
  const italicAfter = diff.after_status !== "verbatim";

  const before = (i: number, segments?: EciDiffSegment[], text?: string): ReactNode => (
    <LineContent text={text} segments={segments} mark="del" quoted={quotedBefore.has(i)} italic={italicBefore && !quotedBefore.has(i)} />
  );
  const after = (i: number, segments?: EciDiffSegment[], text?: string): ReactNode => (
    <LineContent text={text} segments={segments} mark="ins" quoted={quotedAfter.has(i)} italic={italicAfter && !quotedAfter.has(i)} />
  );

  return ops.map((op: EciDiffOp, i): Row => {
    if (op.kind === "same") {
      return { key: `s${i}`, kind: "same", beforeNo: op.a + 1, afterNo: op.b + 1, before: before(op.a, undefined, op.text), after: after(op.b, undefined, op.text) };
    }
    if (op.kind === "del") {
      return { key: `d${i}`, kind: "del", beforeNo: op.a + 1, afterNo: null, before: before(op.a, undefined, op.text), after: null };
    }
    if (op.kind === "add") {
      return { key: `a${i}`, kind: "add", beforeNo: null, afterNo: op.b + 1, before: null, after: after(op.b, undefined, op.text) };
    }
    return { key: `c${i}`, kind: "change", beforeNo: op.a + 1, afterNo: op.b + 1, before: before(op.a, op.before), after: after(op.b, op.after) };
  });
}

function Gutter({ text }: { text: string }) {
  return <span className="eci-diff-gutter mono">{text}</span>;
}

/** The before/after comparison for one rule change: split columns at >=640px, a unified +/- view below
 *  that — both rendered on the server, CSS alone picks which shows, so the diff needs no client JS
 *  (PHASE5-SPEC §6.4). */
export function RuleDiffView({ diff }: { diff: EciRuleDiff }) {
  const rows = buildRows(diff);
  const sidesDiffer = diff.before_status !== diff.after_status;

  return (
    <div>
      {diff.text_status !== "verbatim" && (
        <div role="note" className="eci-diff-callout">
          <svg width="18" height="18" viewBox="0 0 20 20" fill="none" aria-hidden="true" style={{ flexShrink: 0 }}>
            <circle cx="10" cy="10" r="8.5" stroke="currentColor" strokeWidth="1.6" />
            <path d="M10 6v5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
            <circle cx="10" cy="13.6" r="1" fill="currentColor" />
          </svg>
          Built from news reports — not the document&apos;s wording
        </div>
      )}
      {diff.excerpt && (
        <p style={{ fontSize: 12, color: "var(--muted)", margin: "0 0 12px" }}>
          Excerpt: lines outside the change are left out.
        </p>
      )}
      {!sidesDiffer && (
        <div style={{ marginBottom: 10 }}><TextStatusBadge status={diff.text_status} /></div>
      )}
      {diff.text_status !== "verbatim" && (
        <p className="mono" style={{ fontSize: 11, color: "var(--muted)", margin: "0 0 12px" }}>
          &ldquo;&hellip;&rdquo; quoted in reporting &middot; <em>italic</em> = paraphrase
        </p>
      )}

      {/* split view, >=640px (globals.css hides it below that) */}
      <div className="eci-diff-split">
        <div className="eci-diff-col-before" style={{ gridRow: 1, padding: "10px 12px", borderBottom: "1px solid var(--rule)", background: "var(--sunken)" }}>
          <div className="mono" style={{ fontSize: 11, fontWeight: 600, color: "var(--ink2)", marginBottom: sidesDiffer ? 6 : 0 }}>{diff.before_label}</div>
          {sidesDiffer && <TextStatusBadge status={diff.before_status} short />}
        </div>
        <div className="eci-diff-col-after" style={{ gridRow: 1, padding: "10px 12px", borderBottom: "1px solid var(--rule)", background: "var(--sunken)" }}>
          <div className="mono" style={{ fontSize: 11, fontWeight: 600, color: "var(--ink2)", marginBottom: sidesDiffer ? 6 : 0 }}>{diff.after_label}</div>
          {sidesDiffer && <TextStatusBadge status={diff.after_status} short />}
        </div>
        {rows.map((row, i) => (
          <Fragment key={row.key}>
            {row.before !== null && (
              <div className="eci-diff-col-before eci-diff-line" style={{ gridRow: i + 2, color: row.kind === "same" ? "var(--ink2)" : undefined }}>
                <Gutter text={String(row.beforeNo ?? "")} />
                <span>
                  {(row.kind === "del" || row.kind === "change") && <span style={SR_ONLY}>Removed: </span>}
                  {row.before}
                </span>
              </div>
            )}
            {row.after !== null && (
              <div className="eci-diff-col-after eci-diff-line" style={{ gridRow: i + 2, color: row.kind === "same" ? "var(--ink2)" : undefined }}>
                <Gutter text={String(row.afterNo ?? "")} />
                <span>
                  {(row.kind === "add" || row.kind === "change") && <span style={SR_ONLY}>Added: </span>}
                  {row.after}
                </span>
              </div>
            )}
          </Fragment>
        ))}
      </div>

      {/* unified view, <640px */}
      <div className="eci-diff-unified">
        <div style={{ padding: "10px 12px", borderBottom: "1px solid var(--rule)", background: "var(--sunken)" }}>
          <span className="mono" style={{ fontSize: 11, fontWeight: 600, color: "var(--ink2)" }}>{diff.before_label} → {diff.after_label}</span>
          {sidesDiffer && (
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: 8 }}>
              <TextStatusBadge status={diff.before_status} short />
              <TextStatusBadge status={diff.after_status} short />
            </div>
          )}
        </div>
        {rows.map((row) => (
          <Fragment key={row.key}>
            {row.kind === "same" && (
              <div className="eci-diff-line" style={{ color: "var(--ink2)" }}>
                <Gutter text=" " />
                <span>{row.before}</span>
              </div>
            )}
            {(row.kind === "del" || row.kind === "change") && (
              <div className="eci-diff-line" style={{ background: "var(--eci-diff-del-bg)" }}>
                <Gutter text="−" />
                <span><span style={SR_ONLY}>Removed: </span>{row.before}</span>
              </div>
            )}
            {(row.kind === "add" || row.kind === "change") && (
              <div className="eci-diff-line" style={{ background: "var(--eci-diff-add-bg)" }}>
                <Gutter text="+" />
                <span><span style={SR_ONLY}>Added: </span>{row.after}</span>
              </div>
            )}
          </Fragment>
        ))}
      </div>
    </div>
  );
}
