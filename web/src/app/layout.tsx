import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./globals.css";

export const metadata: Metadata = {
  title: "Neta·Resume — the public record of every Indian legislator",
  description:
    "Offices held, parties switched, wealth declared, and cases pending — sourced to the Election Commission and shown without spin.",
};

// Apply the saved theme before paint to avoid a flash of the wrong theme.
const themeInit = `(function(){try{var t=localStorage.getItem('nr-theme');if(t)document.documentElement.setAttribute('data-theme',t);}catch(e){}})();`;

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" data-theme="light" suppressHydrationWarning>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,400..800&family=IBM+Plex+Sans+Devanagari:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap"
          rel="stylesheet"
        />
        <script dangerouslySetInnerHTML={{ __html: themeInit }} />
      </head>
      <body className="scroll">{children}</body>
    </html>
  );
}
