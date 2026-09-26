import Link from "next/link";
import { getEciStates } from "@/lib/api";
import { StatePicker } from "@/components/eci-files/numbers/StatePicker";

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
  { q: "How many names left the rolls?", hint: "Every State and UT, side by side", href: "/eci-files/numbers" },

  // ECI Files phase 5 (PHASE5-SPEC §6.1): four more question cards, appended after phase 3's.
  { q: "What did two Commissioners object to?", hint: "The fourteen objections, dated", href: "/eci-files/objections" },
  { q: "What was charged, and what was the answer?", hint: "Every charge beside its response", href: "/eci-files/answers" },
  { q: "Which rules changed, word for word?", hint: "Before-and-after text comparisons", href: "/eci-files/rules" },
  { q: "Where do the court cases stand?", hint: "Five cases, order by order", href: "/eci-files/courts" },
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

/** "What happened in my state?" (PHASE3-SPEC.md §3.5) — its own async card so a slow/failed
 *  `/eci-files/states` fetch degrades to a plain link rather than blocking the rest of "Start here". */
async function StateQuestionCard() {
  const overview = await getEciStates().catch(() => null);
  if (!overview) {
    return (
      <QuestionCard item={{ q: "What happened in my state?", hint: "Roll figures before, during and after the SIR", href: "/eci-files/numbers" }} />
    );
  }
  return (
    <div className="lift" style={{ border: "1px solid var(--rule)", borderRadius: 12, background: "var(--card2)", padding: "15px 17px" }}>
      <div className="serif" style={{ fontSize: 14.5, fontWeight: 600, lineHeight: 1.3, marginBottom: 5 }}>What happened in my state?</div>
      <div style={{ fontSize: 11.5, color: "var(--muted)", marginBottom: 10 }}>Roll figures before, during and after the SIR</div>
      <StatePicker regions={overview.regions} compact />
    </div>
  );
}

export async function QuestionCards() {
  return (
    <section style={{ marginBottom: 32 }}>
      <h2 className="mono" style={{ fontSize: 11, letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--faint)", margin: "0 0 12px" }}>
        Start here
      </h2>
      <div className="nr-navgrid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))" }}>
        <StateQuestionCard />
        {QUESTIONS.map((item) => (
          <QuestionCard key={item.href} item={item} />
        ))}
      </div>
    </section>
  );
}
