export default function Home() {
  return (
    <main>
      <h1>Neta-Resume</h1>
      <p>
        Structured, source-linked resumes for members of the Lok Sabha, Rajya Sabha, and (later) every
        state legislature in India — office history, party switches, ECI affidavit wealth, and criminal
        cases with severity.
      </p>
      <p style={{ color: "#666" }}>
        Phase 0 scaffold. Search and the person page land in Phase 1. See{" "}
        <code>person/[id]</code> for the resume render target.
      </p>
      <p style={{ fontSize: "0.85rem", color: "#999" }}>
        Non-commercial / hobby project. Criminal cases shown are mostly pending/alleged; status and the
        source are always displayed. Data via ECI affidavits, MyNeta/ADR, Digital Sansad, TCPD and others.
      </p>
    </main>
  );
}
