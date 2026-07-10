import type { Metadata, Viewport } from "next";
import { Suspense, type ReactNode } from "react";
import { Footer } from "@/components/Footer";
import { RouteProgress } from "@/components/RouteProgress";
import "./globals.css";

// Canonical site URL for metadata / OG / canonical links. Defaults to the custom domain (NOT Vercel's
// *.vercel.app alias, which VERCEL_PROJECT_PRODUCTION_URL would give); override per-env if needed.
const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || "https://neta-resume.app";

const DESCRIPTION =
  "Offices held, parties switched, wealth declared, and cases pending — every fact sourced to the " +
  "Election Commission and shown without spin. A free, open public record of every Indian legislator.";

// Explicit mobile viewport. width=device-width + initialScale 1 is Next's default, set here explicitly;
// deliberately NOT locking maximumScale/userScalable so pinch-zoom stays available (accessibility).
export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
};

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: {
    default: "Neta·Resume — the public record of every Indian legislator",
    template: "%s · Neta·Resume",
  },
  description: DESCRIPTION,
  applicationName: "Neta·Resume",
  keywords: [
    "Indian legislators", "Lok Sabha", "Rajya Sabha", "Member of Parliament", "ECI affidavit",
    "criminal cases", "declared assets", "party switches", "public record",
  ],
  openGraph: {
    type: "website",
    siteName: "Neta·Resume",
    url: siteUrl,
    title: "Neta·Resume — the public record of every Indian legislator",
    description:
      "Wealth declared, cases pending, parties switched, offices held — sourced to the Election " +
      "Commission, for every MP.",
  },
  twitter: {
    card: "summary_large_image",
    title: "Neta·Resume — the public record of every Indian legislator",
    description: "The sourced public record of every Indian legislator — wealth, cases, parties, offices.",
  },
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
      <body className="scroll">
        <Suspense fallback={null}><RouteProgress /></Suspense>
        {children}
        <Footer />
      </body>
    </html>
  );
}
