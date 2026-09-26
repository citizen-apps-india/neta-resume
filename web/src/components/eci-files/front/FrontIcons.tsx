// Inline stroke icons for the front page's seven section tiles — generic glyphs (a dotted line, bars, a
// person, a document, a courthouse), recoloured via `currentColor` so each tile's own token drives them
// instead of a baked-in hex.

import type { ReactNode } from "react";

function Svg({ children }: { children: ReactNode }) {
  return (
    <svg width="22" height="22" viewBox="0 0 28 28" fill="none" aria-hidden="true" style={{ display: "block" }}>
      {children}
    </svg>
  );
}

export function TimelineIcon() {
  return (
    <Svg>
      <path d="M3 14h22" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
      <circle cx="8" cy="14" r="2.6" fill="currentColor" />
      <circle cx="14" cy="14" r="3.4" fill="currentColor" />
      <circle cx="21" cy="14" r="2.6" fill="currentColor" />
    </Svg>
  );
}

export function StatesIcon() {
  return (
    <Svg>
      <rect x="4" y="15" width="5" height="9" rx="1" fill="currentColor" />
      <rect x="11.5" y="9" width="5" height="15" rx="1" fill="currentColor" />
      <rect x="19" y="4" width="5" height="20" rx="1" fill="currentColor" />
    </Svg>
  );
}

export function PeopleIcon() {
  return (
    <Svg>
      <circle cx="14" cy="9.5" r="4.3" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M5.5 23c0-4.7 3.8-7.6 8.5-7.6s8.5 2.9 8.5 7.6" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
    </Svg>
  );
}

export function ObjectionsIcon() {
  return (
    <Svg>
      <circle cx="14" cy="14" r="10.5" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M14 8.5v6.5" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="14" cy="19" r="1.3" fill="currentColor" />
    </Svg>
  );
}

export function AnswersIcon() {
  return (
    <Svg>
      <path d="M5 6.5A2 2 0 0 1 7 4.5h14a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H14l-4.5 4v-4H7a2 2 0 0 1-2-2z" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M9.5 11.5l2.7 2.7 6-6" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
    </Svg>
  );
}

export function RulesIcon() {
  return (
    <Svg>
      <rect x="6" y="3.5" width="16" height="21" rx="2" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M9.5 10h9M9.5 14.5h9M9.5 19h6" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
    </Svg>
  );
}

export function CourtsIcon() {
  return (
    <Svg>
      <path d="M14 4v20M8 24h12M5 8h18" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M5 8l-3 6.5a3.3 3.3 0 0 0 6 0z" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M23 8l-3 6.5a3.3 3.3 0 0 0 6 0z" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
    </Svg>
  );
}
