import type { Metadata } from "next";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "Neta-Resume",
  description: "Public-record resumes for Indian legislators. Every fact carries its source.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body style={{ fontFamily: "system-ui, sans-serif", maxWidth: 880, margin: "0 auto", padding: 24 }}>
        <header style={{ borderBottom: "1px solid #eee", paddingBottom: 12, marginBottom: 24 }}>
          <a href="/" style={{ fontWeight: 700, fontSize: "1.25rem", textDecoration: "none", color: "#111" }}>
            Neta-Resume
          </a>
        </header>
        {children}
      </body>
    </html>
  );
}
