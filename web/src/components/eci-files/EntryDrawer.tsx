"use client";

import { useEffect, useRef, type ReactNode } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

/** The drawer chrome: a side panel on desktop, a bottom sheet under 640px (CSS repositions the same
 *  markup — see `.eci-drawer-panel` in globals.css). Esc and the backdrop close it; closing removes
 *  `?entry=` and keeps every other filter/window param, so the URL is always the thing driving it open.
 *  Content is server-rendered (`EntryDetail`) and passed as `children` — this shell owns only the
 *  interactivity REDESIGN-SPEC calls for: "Esc closes the drawer." */
export function EntryDrawer({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const panelRef = useRef<HTMLDivElement>(null);

  function close() {
    const params = new URLSearchParams(searchParams.toString());
    params.delete("entry");
    const qs = params.toString();
    router.push(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
  }

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") close();
    }
    document.addEventListener("keydown", onKey);
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    panelRef.current?.focus();
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = prevOverflow;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <>
      <div className="eci-drawer-backdrop" onClick={close} aria-hidden />
      <div
        ref={panelRef}
        className="eci-drawer-panel"
        role="dialog"
        aria-modal="true"
        aria-label="Entry detail"
        tabIndex={-1}
      >
        <div style={{ position: "sticky", top: 0, display: "flex", justifyContent: "flex-end", padding: "12px 14px 0", background: "var(--panel)", zIndex: 1 }}>
          <button
            type="button"
            className="tap"
            onClick={close}
            aria-label="Close"
            style={{
              width: 34, height: 34, display: "inline-flex", alignItems: "center", justifyContent: "center",
              borderRadius: 8, border: "1px solid var(--border)", background: "var(--card2)", color: "var(--ink2)",
              fontSize: 15, cursor: "pointer",
            }}
          >
            ✕
          </button>
        </div>
        <div style={{ padding: "8px clamp(16px,4vw,26px) 32px" }}>{children}</div>
      </div>
    </>
  );
}
