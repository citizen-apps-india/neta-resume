"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";

/** A filter dropdown that rewrites one query param and keeps the rest (the timeline window, other filters). */
export function FilterSelect({
  id, label, param, value, options, allLabel,
}: {
  id: string;
  label: string;
  param: string;
  value?: string;
  options: { value: string; label: string }[];
  allLabel: string;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  function onChange(next: string) {
    const params = new URLSearchParams(searchParams.toString());
    if (next) params.set(param, next);
    else params.delete(param);
    params.delete("entry");
    const qs = params.toString();
    router.push(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
  }

  return (
    <label htmlFor={id} style={{ display: "inline-flex", alignItems: "center", gap: 8, fontSize: 12, color: "var(--muted)" }}>
      <span className="mono" style={{ fontSize: 10.5, letterSpacing: "0.06em" }}>{label.toUpperCase()}</span>
      <select
        id={id}
        value={value ?? ""}
        onChange={(e) => onChange(e.target.value)}
        className="eci-select"
      >
        <option value="">{allLabel}</option>
        {options.map((o) => (
          <option key={o.value} value={o.value}>{o.label}</option>
        ))}
      </select>
    </label>
  );
}
