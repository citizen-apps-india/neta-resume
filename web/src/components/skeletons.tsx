import type { CSSProperties } from "react";
import { SiteHeader } from "@/components/SiteHeader";

/** A single shimmer block. */
function S({ w = "100%", h, r = 8, style }: { w?: number | string; h: number | string; r?: number; style?: CSSProperties }) {
  return <div className="skeleton" style={{ width: w, height: h, borderRadius: r, ...style }} />;
}

const main: CSSProperties = { maxWidth: 1120, margin: "0 auto", padding: "28px clamp(14px,4vw,28px) 64px", width: "100%" };

/** Loading placeholder for the browse pages (Lok Sabha / Rajya Sabha / Directory / State / Municipal). */
export function ListSkeleton() {
  return (
    <>
      <SiteHeader />
      <main style={main}>
        <S w={280} h={34} style={{ marginBottom: 10 }} />
        <S w={520} h={15} r={6} style={{ maxWidth: "90%", marginBottom: 24 }} />
        <div style={{ border: "1px solid var(--rule)", borderRadius: 14, overflow: "hidden" }}>
          <div style={{ display: "flex", gap: 10, padding: 16, borderBottom: "1px solid var(--rule)", background: "var(--card)", flexWrap: "wrap" }}>
            <S h={38} style={{ flex: "1 1 200px" }} />
            <S w={130} h={38} /><S w={130} h={38} /><S w={150} h={38} />
          </div>
          <div style={{ padding: "12px 22px", background: "var(--sunken)", borderBottom: "1px solid var(--rule)" }}>
            <S w={130} h={13} r={5} />
          </div>
          <div style={{ padding: "clamp(14px,4vw,22px)", display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(min(100%, 270px), 1fr))", gap: 16 }}>
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} style={{ border: "1px solid var(--rule)", borderRadius: 12, background: "var(--card2)", overflow: "hidden" }}>
                <div style={{ display: "flex", gap: 13, padding: 16 }}>
                  <S w={50} h={60} />
                  <div style={{ flex: 1 }}>
                    <S h={16} r={5} style={{ marginBottom: 8 }} />
                    <S w="70%" h={12} r={5} style={{ marginBottom: 12 }} />
                    <S w={110} h={24} r={20} />
                  </div>
                </div>
                <div style={{ display: "flex", borderTop: "1px solid var(--rule)" }}>
                  {[0, 1, 2].map((j) => (
                    <div key={j} style={{ flex: 1, padding: "12px 14px", borderRight: j < 2 ? "1px solid var(--rule)" : "none" }}>
                      <S w="60%" h={13} r={4} />
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </main>
    </>
  );
}

/** Loading placeholder for the person profile — the heaviest, most-clicked route. */
export function ProfileSkeleton() {
  return (
    <>
      <SiteHeader />
      <main style={{ ...main, maxWidth: 980 }}>
        <S w={90} h={12} r={5} style={{ marginBottom: 20 }} />
        <div style={{ display: "flex", gap: 20, marginBottom: 28, flexWrap: "wrap" }}>
          <S w={120} h={150} r={10} />
          <div style={{ flex: 1, minWidth: 240 }}>
            <S w="60%" h={30} r={7} style={{ marginBottom: 12 }} />
            <S w={170} h={26} r={20} style={{ marginBottom: 18 }} />
            <S w="80%" h={14} r={5} style={{ marginBottom: 8 }} />
            <S w="45%" h={14} r={5} />
          </div>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: 12, marginBottom: 28 }}>
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} style={{ border: "1px solid var(--rule)", borderRadius: 12, padding: 16, background: "var(--card2)" }}>
              <S w="55%" h={20} r={5} style={{ marginBottom: 8 }} />
              <S w="70%" h={11} r={4} />
            </div>
          ))}
        </div>
        <div style={{ display: "flex", gap: 16, borderBottom: "1px solid var(--rule)", paddingBottom: 12, marginBottom: 20 }}>
          {Array.from({ length: 5 }).map((_, i) => <S key={i} w={72} h={16} r={5} />)}
        </div>
        <S h={220} r={12} />
      </main>
    </>
  );
}

/** Inline fallback for the homepage's location-based preview (streamed in via <Suspense>). Header-less —
 *  the page shell (hero, stats, features) is already on screen; this only holds the preview card's space. */
export function HomePreviewSkeleton() {
  return (
    <section style={{ padding: "8px clamp(16px,5vw,48px) 64px", maxWidth: 1080, margin: "0 auto", width: "100%" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16 }}>
        <S w={150} h={14} r={6} />
        <S w={92} h={24} r={999} />
      </div>
      <div style={{ border: "1px solid var(--rule)", borderRadius: 14, background: "var(--card2)", overflow: "hidden" }}>
        <div style={{ padding: 22 }}>
          <div style={{ display: "flex", gap: 16 }}>
            <S w={64} h={78} />
            <div style={{ flex: 1 }}>
              <S w="55%" h={24} r={6} style={{ marginBottom: 10 }} />
              <S w={150} h={22} r={20} />
            </div>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 1, marginTop: 18, border: "1px solid var(--rule)", borderRadius: 10, overflow: "hidden" }}>
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} style={{ padding: "12px 14px" }}>
                <S w="70%" h={15} r={4} style={{ marginBottom: 6 }} />
                <S w="90%" h={9} r={3} />
              </div>
            ))}
          </div>
          <S h={120} style={{ marginTop: 18 }} />
        </div>
      </div>
    </section>
  );
}

/** Inline fallback for the Parliament console (streamed in). Header-less — SiteHeader is already rendered. */
export function ConsoleSkeleton() {
  return (
    <div>
      <S w={260} h={30} r={7} style={{ marginBottom: 10 }} />
      <S w={440} h={14} r={6} style={{ maxWidth: "90%", marginBottom: 22 }} />
      <div style={{ display: "flex", gap: 14, borderBottom: "1px solid var(--rule)", paddingBottom: 12, marginBottom: 20 }}>
        {Array.from({ length: 5 }).map((_, i) => <S key={i} w={78} h={16} r={5} />)}
      </div>
      <S h={360} r={12} />
    </div>
  );
}

/** Inline fallback for the India Dashboard body (streamed in below the static SectionHero). Header-less. */
export function DashboardBodySkeleton() {
  return (
    <div>
      <div className="nr-statgrid" style={{ marginBottom: 22 }}>
        {Array.from({ length: 4 }).map((_, i) => <S key={i} h={120} r={14} />)}
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(min(250px, 100%), 1fr))", gap: 12 }}>
        {Array.from({ length: 8 }).map((_, i) => <S key={i} h={150} r={12} />)}
      </div>
    </div>
  );
}

/** Generic placeholder for other pages (home / elections). */
export function PageSkeleton() {
  return (
    <>
      <SiteHeader />
      <main style={main}>
        <S w={320} h={34} style={{ marginBottom: 12 }} />
        <S w={560} h={15} r={6} style={{ maxWidth: "90%", marginBottom: 28 }} />
        <S h={180} r={14} style={{ marginBottom: 16 }} />
        <S h={320} r={14} />
      </main>
    </>
  );
}
