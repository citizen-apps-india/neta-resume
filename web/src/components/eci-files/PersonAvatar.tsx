"use client";

import { useState } from "react";
import type { EciPhoto } from "@/types/eci-files";
import { initials } from "@/lib/eci-files";

/** A photo where the record has one of the five reviewer-confirmed ones, initials otherwise — always the
 *  same size and the same circular frame, so a row of commissioners never reads as a judgment about the
 *  ones shown as initials (docs/eci-files/PHASES-3-5-DECISIONS.md). A client component only so a photo
 *  file the backend hasn't fetched yet (or a bad path) falls back to initials instead of a broken image
 *  icon — `onError` needs to run in the browser.
 *
 *  `decorative`: true when the name is printed right beside the avatar (cards, panel lists) — `alt=""`
 *  there; otherwise `alt="Photo of {name}"`. */
export function PersonAvatar({
  name, photo, size, decorative = false,
}: {
  name: string;
  photo: EciPhoto | null | undefined;
  size: number;
  decorative?: boolean;
}) {
  const [broken, setBroken] = useState(false);
  const fontSize = Math.max(10, Math.round(size * 0.36));

  if (photo && !broken) {
    return (
      <img
        src={photo.url}
        width={size}
        height={size}
        loading="lazy"
        decoding="async"
        className="eci-avatar"
        style={{ width: size, height: size }}
        alt={decorative ? "" : `Photo of ${name}`}
        onError={() => setBroken(true)}
      />
    );
  }

  return (
    <span
      aria-hidden
      className="mono eci-avatar-initials"
      style={{ width: size, height: size, fontSize }}
    >
      {initials(name)}
    </span>
  );
}
