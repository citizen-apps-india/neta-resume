import type { ReactNode } from "react";
import Link from "next/link";
import { eciEntryHref, tokenizeEntryIds } from "@/lib/eci-files";

/** Renders prose (a note, a followed-by line) with any entry-id-shaped token turned into a `?entry=<id>`
 *  drawer link on `basePath` — verbatim, no rewording. First shipped in `numbers/StateNotes.tsx`; reused
 *  wherever a public note otherwise leaked a raw entry id (entry notes, pairs notes, the objections
 *  lede). The drawer renders nothing if the id doesn't exist, same as elsewhere. */
export function LinkifiedNote({ text, basePath }: { text: string; basePath: string }): ReactNode {
  return tokenizeEntryIds(text).map((token, i) =>
    token.kind === "text"
      ? token.text
      : <Link key={i} href={eciEntryHref(token.id, {}, basePath)} style={{ color: "inherit", textDecoration: "underline" }}>{token.id}</Link>,
  );
}
