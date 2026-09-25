import Link from "next/link";

interface Question {
  q: string;
  hint: string;
  href: string;
}

// "Start here" — five neutral, factual entry questions, each into a filtered view (REDESIGN-SPEC §"Web":
// "'Start here' question cards linking to filtered views: timeline by lane or topic, and people"). No
// verdict words (BRIEF.md's stance) — these ask what happened, never assert an answer.
const QUESTIONS: Question[] = [
  { q: "What rules changed, and when?", hint: "Orders, handbooks and forms — Commission lane", href: "/eci-files/timeline?lane=commission" },
  { q: "What did commissioners say internally?", hint: "Recorded dissent and objections — Inside lane", href: "/eci-files/timeline?lane=inside" },
  { q: "What have the courts ordered?", hint: "Supreme Court and High Court cases — Courts lane", href: "/eci-files/timeline?lane=courts" },
  { q: "What has been claimed, and by whom?", hint: "Named claims, attributed — Claims lane", href: "/eci-files/timeline?lane=claims" },
  { q: "How has the Commission answered?", hint: "On-the-record responses — Responses lane", href: "/eci-files/timeline?lane=responses" },
  { q: "Who are the commissioners and officials?", hint: "Profiles, tenure and postings", href: "/eci-files/people" },
];

function QuestionCard({ item }: { item: Question }) {
  return (
    <Link
      href={item.href}
      className="lift tap"
      style={{
        display: "block", textDecoration: "none", color: "var(--ink)",
        border: "1px solid var(--rule)", borderRadius: 12, background: "var(--card2)", padding: "15px 17px",
      }}
    >
      <div className="serif" style={{ fontSize: 14.5, fontWeight: 600, lineHeight: 1.3, marginBottom: 5 }}>{item.q}</div>
      <div style={{ fontSize: 11.5, color: "var(--muted)" }}>{item.hint}</div>
    </Link>
  );
}

export function QuestionCards() {
  return (
    <section style={{ marginBottom: 32 }}>
      <h2 className="mono" style={{ fontSize: 11, letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--faint)", margin: "0 0 12px" }}>
        Start here
      </h2>
      <div className="nr-navgrid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))" }}>
        {QUESTIONS.map((item) => (
          <QuestionCard key={item.href} item={item} />
        ))}
      </div>
    </section>
  );
}
