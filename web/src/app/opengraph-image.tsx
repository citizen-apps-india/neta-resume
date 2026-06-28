import { ImageResponse } from "next/og";

export const alt = "Neta·Resume — the public record of every Indian legislator";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

// Branded social-share card, generated at build/request time (no static asset needed).
// Note: keep to Latin glyphs only — exotic glyphs trigger a dynamic font fetch; and every element with
// more than one child must set display:flex (Satori requirement).
export default function OpengraphImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          background: "#F5F6F7",
          padding: "72px 80px",
          fontFamily: "sans-serif",
        }}
      >
        <div style={{ display: "flex", alignItems: "center" }}>
          <div
            style={{
              width: 56, height: 56, borderRadius: 12, background: "#12A594",
              display: "flex", alignItems: "center", justifyContent: "center", color: "#fff",
              fontSize: 26, fontWeight: 700,
            }}
          >
            NR
          </div>
          <div style={{ display: "flex", fontSize: 30, fontWeight: 700, color: "#121317", marginLeft: 18 }}>
            Neta-Resume
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column" }}>
          <div style={{ display: "flex", fontSize: 64, fontWeight: 700, color: "#121317", lineHeight: 1.1, letterSpacing: -1.5 }}>
            The public record of every Indian legislator.
          </div>
          <div style={{ display: "flex", fontSize: 28, color: "#4B4F59", marginTop: 22 }}>
            Wealth declared. Cases pending. Parties switched. Offices held.
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center" }}>
          <div style={{ width: 40, height: 6, borderRadius: 3, background: "#12A594" }} />
          <div style={{ display: "flex", fontSize: 22, color: "#6B7280", marginLeft: 14 }}>
            Sourced to the Election Commission of India - open and non-commercial
          </div>
        </div>
      </div>
    ),
    { ...size },
  );
}
