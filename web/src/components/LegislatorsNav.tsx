"use client";

import Link from "next/link";
import { Fragment, useCallback, useEffect, useRef, useState } from "react";

/** [href, pill label (short — the pill must fit in the nav bar), panel label (full)] */
const HOUSES: [string, string, string][] = [
  ["/lok-sabha", "Lok Sabha", "Lok Sabha"],
  ["/rajya-sabha", "Rajya Sabha", "Rajya Sabha"],
  ["/state-level", "State", "State Level"],
  ["/municipal", "Municipal", "Municipal"],
];

/**
 * The "Legislators" nav item, housing the four browse scopes.
 * - `desktop`: clicking the word morphs it in place into a pill row of the house links, pushing the
 *   nav siblings aside; ✕ / Escape / outside-click / navigating collapses it back.
 * - `panel`: the hamburger-menu variant — an accordion that expands the links downward instead.
 */
export function LegislatorsNav({
  variant = "desktop",
  onNavigate,
}: {
  variant?: "desktop" | "panel";
  onNavigate?: () => void;
}) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLSpanElement>(null);
  const wordRef = useRef<HTMLButtonElement>(null);
  const firstLinkRef = useRef<HTMLAnchorElement>(null);

  const close = useCallback((refocus: boolean) => {
    setOpen(false);
    if (refocus) wordRef.current?.focus({ preventScroll: true });
  }, []);

  // Collapse the pill when the user clicks anywhere else in the page.
  useEffect(() => {
    if (!open || variant !== "desktop") return;
    const onDown = (e: PointerEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("pointerdown", onDown);
    return () => document.removeEventListener("pointerdown", onDown);
  }, [open, variant]);

  // Hand keyboard users the first house link as soon as the pill opens.
  useEffect(() => {
    if (open && variant === "desktop") firstLinkRef.current?.focus({ preventScroll: true });
  }, [open, variant]);

  if (variant === "panel") {
    return (
      <div className="nr-morph-acc">
        <button
          className={`nr-morph-acc-head${open ? " open" : ""}`}
          aria-expanded={open}
          onClick={() => setOpen((o) => !o)}
        >
          Legislators
          <span aria-hidden className="nr-morph-acc-chev">▸</span>
        </button>
        <div className={`nr-morph-acc-list${open ? " open" : ""}`}>
          {HOUSES.map(([href, , full], i) => (
            <Link
              key={href}
              className="navlink nr-morph-acc-item"
              href={href}
              style={{ ["--i" as string]: i }}
              tabIndex={open ? 0 : -1}
              onClick={() => {
                setOpen(false);
                onNavigate?.();
              }}
            >
              {full}
            </Link>
          ))}
        </div>
      </div>
    );
  }

  return (
    <span
      ref={rootRef}
      className={`nr-morph${open ? " open" : ""}`}
      onKeyDown={(e) => {
        if (e.key === "Escape" && open) {
          e.stopPropagation();
          close(true);
        }
      }}
    >
      <button
        ref={wordRef}
        className="navlink nr-morph-word"
        aria-expanded={open}
        tabIndex={open ? -1 : 0}
        onClick={() => setOpen(true)}
      >
        Legislators
        <span aria-hidden>▸</span>
      </button>

      <span className="nr-morph-pill" aria-hidden={!open}>
        {HOUSES.map(([href, short], i) => (
          <Fragment key={href}>
            {i > 0 && (
              <span aria-hidden className="nr-morph-sep" style={{ ["--i" as string]: i }}>
                ·
              </span>
            )}
            <Link
              ref={i === 0 ? firstLinkRef : undefined}
              className="navlink nr-morph-item"
              href={href}
              style={{ ["--i" as string]: i }}
              tabIndex={open ? 0 : -1}
              onClick={() => setOpen(false)}
            >
              {short}
            </Link>
          </Fragment>
        ))}
        <button
          className="nr-morph-close"
          aria-label="Close legislators menu"
          tabIndex={open ? 0 : -1}
          style={{ ["--i" as string]: HOUSES.length }}
          onClick={() => close(true)}
        >
          ✕
        </button>
      </span>
    </span>
  );
}
