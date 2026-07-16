"use client";

import { useEffect, useRef, useState } from "react";

/** Sticky anchor rail for the India Dashboard: one chip per category, each scrolling to its section.
 *  Pins just below the (also-sticky) site header — it measures the header height at runtime and publishes
 *  it as CSS vars so the rail offset and the sections' scroll-margin adapt to it. The active chip tracks
 *  the section in view and is kept scrolled into view; a vertical wheel scrolls the rail horizontally when
 *  it overflows. Purely a navigation aid — no data. */
export function CategoryRail({ items }: { items: { name: string; slug: string }[] }) {
  const [active, setActive] = useState(items[0]?.slug ?? "");
  const railRef = useRef<HTMLElement>(null);

  // Publish header + rail geometry as CSS vars so the rail sticks below the header and anchored sections
  // land below both. Re-measured on resize (header height changes between desktop/mobile).
  useEffect(() => {
    const sync = () => {
      const header = document.querySelector("header");
      const headerH = header ? Math.round(header.getBoundingClientRect().height) : 64;
      const railH = railRef.current ? Math.round(railRef.current.getBoundingClientRect().height) : 48;
      const root = document.documentElement;
      root.style.setProperty("--nr-rail-top", `${headerH}px`);
      root.style.setProperty("--nr-anchor-offset", `${headerH + railH + 14}px`);
    };
    sync();
    window.addEventListener("resize", sync);
    return () => window.removeEventListener("resize", sync);
  }, [items]);

  // Track the section in view (topmost intersecting within the rail-offset band).
  useEffect(() => {
    const sections = items
      .map((it) => document.getElementById(it.slug))
      .filter((el): el is HTMLElement => el != null);
    if (!sections.length) return;

    const obs = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
        if (visible[0]) setActive(visible[0].target.id);
      },
      { rootMargin: "-118px 0px -55% 0px", threshold: 0 },
    );
    sections.forEach((s) => obs.observe(s));
    return () => obs.disconnect();
  }, [items]);

  // Keep the highlighted chip visible as you scroll through sections.
  useEffect(() => {
    const rail = railRef.current;
    if (!rail) return;
    const chip = rail.querySelector<HTMLElement>(`[data-slug="${active}"]`);
    if (!chip) return;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    chip.scrollIntoView({ inline: "center", block: "nearest", behavior: reduce ? "auto" : "smooth" });
  }, [active]);

  // Translate a vertical wheel gesture into horizontal scroll when the rail overflows. React's onWheel is
  // passive (can't preventDefault), so attach natively with { passive: false }.
  useEffect(() => {
    const rail = railRef.current;
    if (!rail) return;
    const onWheel = (e: WheelEvent) => {
      if (rail.scrollWidth <= rail.clientWidth) return; // fits — let the page scroll normally
      if (Math.abs(e.deltaY) <= Math.abs(e.deltaX)) return; // already a horizontal gesture
      rail.scrollLeft += e.deltaY;
      e.preventDefault();
    };
    rail.addEventListener("wheel", onWheel, { passive: false });
    return () => rail.removeEventListener("wheel", onWheel);
  }, [items]);

  return (
    <nav ref={railRef} className="nr-cat-rail" aria-label="Dashboard sections">
      {items.map((it) => (
        <a
          key={it.slug}
          href={`#${it.slug}`}
          data-slug={it.slug}
          className={`nr-cat-chip${active === it.slug ? " active" : ""}`}
          aria-current={active === it.slug ? "true" : undefined}
        >
          {it.name}
        </a>
      ))}
    </nav>
  );
}
