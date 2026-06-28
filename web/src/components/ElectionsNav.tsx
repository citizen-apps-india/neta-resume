"use client";

import Link from "next/link";
import { useCallback, useRef, useState } from "react";

const COLORS = ["var(--accent)", "var(--accent-2)", "var(--ok)", "#f5a623", "#e2466b", "#7c5cff", "#22b8cf"];

type Piece = { id: number; dx: number; dy: number; rot: number; color: string; delay: number; size: number };

/** The "Elections" nav item — a little confetti burst on hover + a "Celebration of Democracy" tooltip. */
export function ElectionsNav({
  onClick,
  style,
}: {
  onClick?: () => void;
  style?: React.CSSProperties;
}) {
  const [pieces, setPieces] = useState<Piece[]>([]);
  const [hovered, setHovered] = useState(false);
  const seq = useRef(0);

  const burst = useCallback(() => {
    setHovered(true);
    // Respect reduced-motion: tooltip only, no confetti.
    if (typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) return;
    const batch: Piece[] = Array.from({ length: 16 }, () => {
      const angle = Math.random() * Math.PI * 2;
      const dist = 18 + Math.random() * 26;
      return {
        id: seq.current++,
        dx: Math.cos(angle) * dist,
        dy: Math.sin(angle) * dist - 10, // bias upward
        rot: (Math.random() - 0.5) * 540,
        color: COLORS[Math.floor(Math.random() * COLORS.length)],
        delay: Math.random() * 80,
        size: 4 + Math.random() * 4,
      };
    });
    setPieces((p) => [...p, ...batch]);
    const ids = new Set(batch.map((b) => b.id));
    window.setTimeout(() => setPieces((p) => p.filter((x) => !ids.has(x.id))), 1000);
  }, []);

  return (
    <span style={{ position: "relative", display: "inline-flex" }} onMouseLeave={() => setHovered(false)}>
      <Link
        className="navlink"
        href="/elections"
        title="Celebration of Democracy"
        onMouseEnter={burst}
        onFocus={burst}
        onClick={onClick}
        style={style}
      >
        Elections
      </Link>

      {/* tooltip */}
      <span
        aria-hidden
        style={{
          position: "absolute", top: "calc(100% + 8px)", left: "50%", transform: "translateX(-50%)",
          whiteSpace: "nowrap", fontSize: 11, fontWeight: 600, letterSpacing: "0.02em",
          padding: "5px 10px", borderRadius: 7, background: "var(--ink)", color: "var(--bg)",
          boxShadow: "0 6px 18px -8px var(--shadow)", pointerEvents: "none", zIndex: 30,
          opacity: hovered ? 1 : 0, transition: "opacity .15s ease",
        }}
      >
        🎉 Celebration of Democracy
      </span>

      {/* confetti */}
      <span aria-hidden style={{ position: "absolute", top: "50%", left: "50%", width: 0, height: 0, pointerEvents: "none" }}>
        {pieces.map((p) => (
          <span
            key={p.id}
            style={{
              position: "absolute", width: p.size, height: p.size, background: p.color, borderRadius: 1,
              // animation drives a CSS custom-property-based translate/rotate (see globals.css nrConfetti)
              ["--dx" as string]: `${p.dx}px`, ["--dy" as string]: `${p.dy}px`, ["--rot" as string]: `${p.rot}deg`,
              animation: `nrConfetti 0.9s ${p.delay}ms ease-out forwards`,
            }}
          />
        ))}
      </span>
    </span>
  );
}
