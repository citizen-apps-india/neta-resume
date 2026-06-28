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
              width: 64, height: 64, borderRadius: 14, background: "#fff",
              display: "flex", alignItems: "center", justifyContent: "center", border: "1px solid #E2E5E8",
            }}
          >
            <svg width="46" height="46" viewBox="0 0 282 282" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M92 92H190.28V109.472H175.928V189.032H154.088V148.316H131V151.748C131 160.952 127.1 165.164 120.08 165.164C109.784 165.164 96.836 151.28 96.836 140.984C96.836 134.9 99.488 130.844 109.004 130.844H154.088V109.472H92V92Z" fill="#121317" />
            </svg>
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
