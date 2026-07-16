"use client";

import { useEffect, useState } from "react";

/** Sticky anchor rail for the India Dashboard: one chip per category, each scrolling to its section.
 *  The active chip tracks the section currently in view (IntersectionObserver). Horizontally scrollable
 *  on narrow screens. Purely a navigation aid — no data. */
export function CategoryRail({ items }: { items: { name: string; slug: string }[] }) {
  const [active, setActive] = useState(items[0]?.slug ?? "");

  useEffect(() => {
    const sections = items
      .map((it) => document.getElementById(it.slug))
      .filter((el): el is HTMLElement => el != null);
    if (!sections.length) return;

    const obs = new IntersectionObserver(
      (entries) => {
        // The topmost section intersecting the rail-offset band wins.
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
        if (visible[0]) setActive(visible[0].target.id);
      },
      { rootMargin: "-96px 0px -55% 0px", threshold: 0 },
    );
    sections.forEach((s) => obs.observe(s));
    return () => obs.disconnect();
  }, [items]);

  return (
    <nav className="nr-cat-rail" aria-label="Dashboard sections">
      {items.map((it) => (
        <a
          key={it.slug}
          href={`#${it.slug}`}
          className={`nr-cat-chip${active === it.slug ? " active" : ""}`}
          aria-current={active === it.slug ? "true" : undefined}
        >
          {it.name}
        </a>
      ))}
    </nav>
  );
}
