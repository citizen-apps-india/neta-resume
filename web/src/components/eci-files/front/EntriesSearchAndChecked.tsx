"use client";

import { useRef, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

/** The search box and "checked only" toggle: both just rewrite the URL (`q`, `checked`), same pattern as
 *  `FilterSelect`, so every other filter and the year stay put. Search is debounced; the checkbox commits
 *  immediately. */
export function EntriesSearchAndChecked({ q, checked }: { q?: string; checked?: boolean }) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [value, setValue] = useState(q ?? "");
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  function commit(next: URLSearchParams) {
    next.delete("entry");
    const qs = next.toString();
    router.push(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
  }

  function onSearchChange(v: string) {
    setValue(v);
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => {
      const next = new URLSearchParams(searchParams.toString());
      if (v.trim()) next.set("q", v.trim());
      else next.delete("q");
      commit(next);
    }, 300);
  }

  function onCheckedChange(v: boolean) {
    const next = new URLSearchParams(searchParams.toString());
    if (v) next.set("checked", "1");
    else next.delete("checked");
    commit(next);
  }

  return (
    <>
      <label htmlFor="eci-entries-search" style={{ position: "absolute", width: 1, height: 1, overflow: "hidden", clip: "rect(0 0 0 0)" }}>
        Search the record
      </label>
      <input
        id="eci-entries-search"
        type="search"
        placeholder="Search titles and people"
        value={value}
        onChange={(e) => onSearchChange(e.target.value)}
        style={{
          flexGrow: 1, minWidth: 200, minHeight: 42, padding: "0 14px", borderRadius: 10,
          border: "1px solid var(--border)", fontSize: 14.5, background: "var(--bg)", color: "var(--ink)",
        }}
      />
      <label style={{ display: "inline-flex", gap: 8, alignItems: "center", fontSize: 13.5, color: "var(--ink2)", minHeight: 42, whiteSpace: "nowrap" }}>
        <input type="checkbox" checked={!!checked} onChange={(e) => onCheckedChange(e.target.checked)} />
        Checked only
      </label>
    </>
  );
}
