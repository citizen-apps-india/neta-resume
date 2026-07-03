"use client";

import { useEffect, useState } from "react";

// The Google Form that collects discrepancy reports. Override per-environment with
// NEXT_PUBLIC_REPORT_FORM_URL; NEXT_PUBLIC_REPORT_FORM_MP_ENTRY is the form's "which MP/page" field id
// (entry.<digits>) used to pre-fill the report from a specific profile.
const FORM_URL =
  process.env.NEXT_PUBLIC_REPORT_FORM_URL ||
  "https://docs.google.com/forms/d/e/1FAIpQLSc4YjmelSr8pnM8fPLKcOYj9wBsYNm7cTj3iLF2BGmGz87GpA/viewform";
const MP_ENTRY = process.env.NEXT_PUBLIC_REPORT_FORM_MP_ENTRY; // e.g. "entry.123456789"

function embedUrl(prefill?: string): string {
  const sep = FORM_URL.includes("?") ? "&" : "?";
  let url = `${FORM_URL}${sep}embedded=true`;
  if (prefill && MP_ENTRY) url += `&${MP_ENTRY}=${encodeURIComponent(prefill)}`;
  return url;
}

/** Button + modal that embeds the discrepancy-report Google Form. `prefill` ties it to a record. */
export function ReportDiscrepancyButton({
  prefill,
  variant = "dark",
  label = "Report a discrepancy",
}: {
  prefill?: string;
  variant?: "dark" | "ghost";
  label?: string;
}) {
  const [open, setOpen] = useState(false);
  const [formLoaded, setFormLoaded] = useState(false);

  useEffect(() => {
    if (!open) return;
    setFormLoaded(false); // show the spinner until the embedded form finishes loading
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [open]);

  const triggerStyle: React.CSSProperties =
    variant === "dark"
      ? {
          fontFamily: "'Bricolage Grotesque',sans-serif", fontSize: 12.5, fontWeight: 600,
          padding: "8px 16px", borderRadius: 8, border: "none", background: "var(--btn-bg)",
          color: "var(--btn-fg)", cursor: "pointer",
        }
      : {
          fontFamily: "'Bricolage Grotesque',sans-serif", fontSize: 12.5, fontWeight: 600,
          padding: "8px 14px", borderRadius: 8, border: "1px solid var(--border)",
          background: "transparent", color: "var(--ink2)", cursor: "pointer",
        };

  return (
    <>
      <button
        type="button"
        className={variant === "dark" ? "btnDark" : "btnGhost"}
        style={triggerStyle}
        onClick={() => setOpen(true)}
      >
        {label}
      </button>

      {open && (
        <div
          onClick={() => setOpen(false)}
          style={{
            position: "fixed", inset: 0, zIndex: 100, background: "rgba(8,10,12,0.55)",
            display: "flex", alignItems: "center", justifyContent: "center", padding: 20,
            backdropFilter: "blur(2px)", animation: "nrFadeUp 0.18s ease",
          }}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            style={{
              width: "min(680px, 100%)", maxHeight: "90vh", display: "flex", flexDirection: "column",
              background: "var(--card)", border: "1px solid var(--border)", borderRadius: 14,
              overflow: "hidden", boxShadow: "0 30px 80px -28px rgba(0,0,0,0.5)",
            }}
          >
            <div
              style={{
                display: "flex", alignItems: "center", justifyContent: "space-between",
                padding: "16px 20px", borderBottom: "1px solid var(--rule)", background: "var(--panel)",
              }}
            >
              <div>
                <div className="serif" style={{ fontSize: 16, fontWeight: 600 }}>Report a discrepancy</div>
                <div style={{ fontSize: 12, color: "var(--muted)", marginTop: 2 }}>
                  {prefill ? `About: ${prefill}` : "Spotted a wrong or missing fact? Tell us."}
                </div>
              </div>
              <button
                type="button"
                aria-label="Close"
                className="tap"
                onClick={() => setOpen(false)}
                style={{
                  border: "none", background: "transparent", color: "var(--ink2)", fontSize: 22,
                  lineHeight: 1, cursor: "pointer", padding: 4, borderRadius: 6,
                }}
              >
                ×
              </button>
            </div>
            <div style={{ position: "relative", height: "70vh" }}>
              {!formLoaded && (
                <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 12, background: "var(--card)" }}>
                  <span className="spinner" aria-hidden />
                  <span className="mono" style={{ fontSize: 11, color: "var(--muted)", letterSpacing: "0.05em" }}>LOADING FORM…</span>
                </div>
              )}
              <iframe
                title="Report a discrepancy"
                src={embedUrl(prefill)}
                onLoad={() => setFormLoaded(true)}
                style={{ width: "100%", height: "100%", border: "none", background: "var(--card)" }}
              />
            </div>
          </div>
        </div>
      )}
    </>
  );
}
