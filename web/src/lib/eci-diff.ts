// Line- and word-level diff for /eci-files/rules/[diff] (PHASE5-SPEC §6.4). Pure, no dependencies — the
// API returns lines; the web computes the diff, so the logic lives in one place next to its renderer.

export interface EciDiffSegment {
  text: string;
  changed: boolean;
}

export type EciDiffOp =
  | { kind: "same"; text: string; a: number; b: number }
  | { kind: "del"; text: string; a: number }
  | { kind: "add"; text: string; b: number }
  | { kind: "change"; a: number; b: number; before: EciDiffSegment[]; after: EciDiffSegment[] };

type RawOp =
  | { kind: "same"; text: string; a: number; b: number }
  | { kind: "del"; text: string; a: number }
  | { kind: "add"; text: string; b: number };

/** Exact-equality LCS between two token sequences (lines, or later, words within one changed line). */
function sequenceDiff(a: string[], b: string[]): RawOp[] {
  const n = a.length;
  const m = b.length;
  const dp: number[][] = Array.from({ length: n + 1 }, () => new Array<number>(m + 1).fill(0));
  for (let i = n - 1; i >= 0; i--) {
    for (let j = m - 1; j >= 0; j--) {
      dp[i][j] = a[i] === b[j] ? dp[i + 1][j + 1] + 1 : Math.max(dp[i + 1][j], dp[i][j + 1]);
    }
  }
  const ops: RawOp[] = [];
  let i = 0;
  let j = 0;
  while (i < n && j < m) {
    if (a[i] === b[j]) {
      ops.push({ kind: "same", text: a[i], a: i, b: j });
      i++; j++;
    } else if (dp[i + 1][j] >= dp[i][j + 1]) {
      ops.push({ kind: "del", text: a[i], a: i });
      i++;
    } else {
      ops.push({ kind: "add", text: b[j], b: j });
      j++;
    }
  }
  while (i < n) { ops.push({ kind: "del", text: a[i], a: i }); i++; }
  while (j < m) { ops.push({ kind: "add", text: b[j], b: j }); j++; }
  return ops;
}

/** Adjacent segments of the same `changed` flag collapse into one, so a run of unchanged words doesn't
 *  fragment into one `<span>` per token. */
function mergeSegments(segs: EciDiffSegment[]): EciDiffSegment[] {
  const out: EciDiffSegment[] = [];
  for (const s of segs) {
    const last = out[out.length - 1];
    if (last && last.changed === s.changed) last.text += s.text;
    else out.push({ ...s });
  }
  return out;
}

/** Word-level LCS over one paired before/after line, splitting on whitespace runs (kept as their own
 *  tokens) so spacing is preserved exactly. */
function wordDiff(before: string, after: string): { before: EciDiffSegment[]; after: EciDiffSegment[] } {
  const a = before.split(/(\s+)/).filter((t) => t.length > 0);
  const b = after.split(/(\s+)/).filter((t) => t.length > 0);
  const ops = sequenceDiff(a, b);
  const beforeSegs: EciDiffSegment[] = [];
  const afterSegs: EciDiffSegment[] = [];
  for (const op of ops) {
    if (op.kind === "same") {
      beforeSegs.push({ text: op.text, changed: false });
      afterSegs.push({ text: op.text, changed: false });
    } else if (op.kind === "del") {
      beforeSegs.push({ text: op.text, changed: true });
    } else {
      afterSegs.push({ text: op.text, changed: true });
    }
  }
  return { before: mergeSegments(beforeSegs), after: mergeSegments(afterSegs) };
}

/** Line-level LCS, then each run of consecutive dels followed by consecutive adds is paired index by
 *  index into a `change` op (word-level segments inside); unpaired leftovers stay `del`/`add`. */
export function diffLines(before: string[], after: string[]): EciDiffOp[] {
  const raw = sequenceDiff(before, after);
  const out: EciDiffOp[] = [];
  let i = 0;
  while (i < raw.length) {
    const op = raw[i];
    if (op.kind === "same") {
      out.push(op);
      i++;
      continue;
    }
    const dels: Extract<RawOp, { kind: "del" }>[] = [];
    while (i < raw.length && raw[i].kind === "del") { dels.push(raw[i] as Extract<RawOp, { kind: "del" }>); i++; }
    const adds: Extract<RawOp, { kind: "add" }>[] = [];
    while (i < raw.length && raw[i].kind === "add") { adds.push(raw[i] as Extract<RawOp, { kind: "add" }>); i++; }
    const pairCount = Math.min(dels.length, adds.length);
    for (let k = 0; k < pairCount; k++) {
      const segs = wordDiff(dels[k].text, adds[k].text);
      out.push({ kind: "change", a: dels[k].a, b: adds[k].b, before: segs.before, after: segs.after });
    }
    for (let k = pairCount; k < dels.length; k++) out.push(dels[k]);
    for (let k = pairCount; k < adds.length; k++) out.push(adds[k]);
  }
  return out;
}
