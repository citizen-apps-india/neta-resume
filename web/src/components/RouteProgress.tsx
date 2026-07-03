"use client";

import { useEffect, useRef, useState } from "react";
import { usePathname, useSearchParams } from "next/navigation";

/** Slim top progress bar shown during navigations. Because every page is `force-dynamic` (server-blocking),
 *  a click otherwise looks frozen; this starts on an internal <a> click (or a `nr:nav` event for
 *  router.push callers) and completes when the route commits. */
export function RouteProgress() {
  const pathname = usePathname();
  const search = useSearchParams();
  const [pct, setPct] = useState(0);
  const [visible, setVisible] = useState(false);
  const active = useRef(false);
  const trickle = useRef<ReturnType<typeof setInterval> | null>(null);
  const hide = useRef<ReturnType<typeof setTimeout> | null>(null);
  const safety = useRef<ReturnType<typeof setTimeout> | null>(null);

  function clearTimers() {
    if (trickle.current) { clearInterval(trickle.current); trickle.current = null; }
    if (safety.current) { clearTimeout(safety.current); safety.current = null; }
  }

  function start() {
    if (active.current) return;
    active.current = true;
    if (hide.current) { clearTimeout(hide.current); hide.current = null; }
    clearTimers();
    setVisible(true);
    setPct(8);
    trickle.current = setInterval(() => {
      setPct((p) => (p < 90 ? p + Math.max(0.5, (90 - p) * 0.08) : p));
    }, 200);
    safety.current = setTimeout(() => finish(), 12000); // never let it stick
  }

  function finish() {
    if (!active.current) return;
    active.current = false;
    clearTimers();
    setPct(100);
    hide.current = setTimeout(() => { setVisible(false); setPct(0); }, 320);
  }

  // Navigation start: internal same-origin link clicks + a custom event for programmatic pushes.
  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      const a = (e.target as HTMLElement)?.closest?.("a");
      if (!a) return;
      const href = a.getAttribute("href");
      if (!href || href.startsWith("#") || a.target === "_blank" || a.hasAttribute("download")) return;
      try {
        const url = new URL(a.href, window.location.href);
        if (url.origin !== window.location.origin) return;
        if (url.pathname === window.location.pathname && url.search === window.location.search) return;
      } catch { return; }
      start();
    }
    const onNav = () => start();
    document.addEventListener("click", onClick, true);
    window.addEventListener("nr:nav", onNav);
    return () => {
      document.removeEventListener("click", onClick, true);
      window.removeEventListener("nr:nav", onNav);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // The route committed (pathname or query changed) -> complete the bar.
  useEffect(() => {
    if (active.current) finish();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pathname, search]);

  useEffect(() => () => { clearTimers(); if (hide.current) clearTimeout(hide.current); }, []);

  if (!visible && pct === 0) return null;
  return (
    <div
      className="nr-progress"
      aria-hidden
      style={{ width: `${pct}%`, opacity: visible ? 1 : 0, transition: "width .2s ease, opacity .3s ease" }}
    />
  );
}
