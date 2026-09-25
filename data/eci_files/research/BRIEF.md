# ECI Files — research brief

ECI Files is a new neta-resume section: a sourced, dated record of the Election Commission of India
from **1 January 2019 to today (25 September 2026)**. It covers who the commissioners and senior officials are
and how they were chosen, what rules they made, what the courts ordered, what the numbers are, and what
was said on the record by the Commission, its members, the government and the opposition.

The trigger is the Indian Express investigation of 23 Sep 2026 (Ritika Chopra), "14 times in 10 months, two
Election Commissioners objected on record to poll panel steps":
https://indianexpress.com/article/express-exclusive/election-commission-sir-14-objections-gyanesh-kumar-sukhbir-singh-sandhu-vivek-joshi-10889737/

## The stance (non-negotiable)

This is a **sourced record**, not an argument.

- **Every entry needs at least one source URL.** No source means no entry. If a fact is widely "known" but you can't find a source, log it under `gaps` instead.
- **Prefer primary documents.** Use these first:
  - ECI orders, press notes and handbooks (eci.gov.in)
  - the Gazette of India (egazette.gov.in)
  - Supreme Court and High Court orders (sci.gov.in, main.sci.gov.in, High Court sites, indiankanoon.org)
  - Parliament questions and answers (sansad.in)
  - Acts and bills (indiacode.nic.in, prsindia.org)
  - DoPT and civil-list service records

  Use news reports when no primary document exists, and label them as reports.
- **Label honestly** with the `status` field:
  - `documented` means you opened a primary document that shows it.
  - `reported` means a credible outlet reports it, including where the outlet says it has seen a non-public file.
  - `claim` means a person or party asserts it.
  - `response` means the Commission or an official answering a charge.
- **Attribute claims.** Every `claim` and `response` names who said it in `attributed_to`.
- **Pair charges with answers.** When you record a charge against the Commission or a named person, look for their response and record it as its own `response` entry. If they declined or didn't reply, say so in the charge's `notes`.
- **Write neutrally.** Use no verdict words in our own voice ("rigged", "stolen", "illegal") unless you're quoting someone and attributing it.
- **Don't copy articles.** Summaries are in your own words. A quote is optional, under 15 words, and only where the exact wording matters, such as the text of a legal provision or a recorded objection.
- **Officials' profiles** are public-service records only: postings, roles and documented actions. No family, home, health or personal-life details, even if published.
- **Verify dates.** Use YYYY-MM-DD when known, and set `date_precision` to `day`, `month` or `year` otherwise. Never guess a day.

## Fetching tips

- indianexpress.com blocks the WebFetch tool. Use curl with a browser user-agent and read the article text from the page's `application/ld+json` block (the `articleBody` field). Example:
  `curl -sL -A "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 Chrome/128 Safari/537.36" <url>`
  then extract `articleBody` with python.
- For pages that fail or may change, check `https://web.archive.org/web/2026*/<url>` or `http://archive.org/wayback/available?url=<url>`. Record any archive URL you find in `archive_url`.
- ECI and court sites are often slow or blocked. Try the Wayback copy, the PIB (pib.gov.in) press release, the Parliament answer, or indiankanoon.org before falling back to reporting.

## Output format

Write one JSON file per research area to `data/eci_files/research/<area>.json` (the area slug is given in your task). Use this shape:

```json
{
  "area": "<area slug>",
  "researched_on": "2026-09-25",
  "entries": [
    {
      "id": "<area>-<short-kebab-slug>",
      "kind": "event | person | rule | figure | case | statement",
      "date": "2025-06-24",
      "date_precision": "day | month | year",
      "title": "Short factual headline, under 14 words",
      "summary": "What happened, in your own words, 1-4 sentences, neutral.",
      "status": "documented | reported | claim | response",
      "attributed_to": "Who said it (claims/responses only), else null",
      "people": ["Full names of commissioners/officials involved"],
      "states": ["State/UT names if state-specific"],
      "topics": ["appointments | sir | rolls | forms | it-systems | courts | mcc | turnout-data | evm-vvpat | dissent | numbers | elections-2019 | elections-2024 | statements"],
      "figures": [{"label": "names deleted from draft roll", "value": 6500000, "unit": "electors", "as_of": "2025-08-01"}],
      "details": {},
      "sources": [
        {
          "url": "https://...",
          "publisher": "Election Commission of India",
          "title": "Document or article title",
          "published": "2025-06-24",
          "tier": 1,
          "archive_url": null,
          "quote": null
        }
      ],
      "response_to": "<id of the charge this responds to, for status=response>",
      "notes": "Caveats, conflicting numbers, what is not public, who declined to comment."
    }
  ],
  "gaps": ["Things that should be in the record but that you could not source, and where someone should look."]
}
```

Tiers: 1 is an official or primary document. 2 is research bodies such as PRS or ADR, or a court filing reported verbatim. 3 is news reporting or a statement reported by the press.

**People entries** (`kind: "person"`) put the profile in `details`:

```json
{
  "role": "Chief Election Commissioner",
  "tenure": [{"office": "Election Commissioner", "from": "2024-03-15", "to": "2025-02-18"}],
  "service": "IAS, Kerala cadre, 1988 batch",
  "career": [{"from": "2019-08", "to": "2021-05", "post": "Joint Secretary, Kashmir division, MHA", "source_url": "https://..."}],
  "selection": "How they were selected: panel members, date, any recorded dissent, with source_url",
  "education": "Only if in an official bio"
}
```

Every career line carries its own `source_url`.

Each area finishes by returning a short summary: the entry count, the count per status, and the three most important gaps.
