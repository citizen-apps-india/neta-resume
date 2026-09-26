# ECI Files redesign — phases 1 and 2 spec

The plan and reasoning are in the redesign artifact. This file is the build contract. Read `SPEC.md` first:
this builds on it. Stance rules still apply, as set out in `data/eci_files/research/BRIEF.md`.

The goal is three reading depths. A 60-second front page, a 5-minute lane timeline, and the full sourced
entries one tap away.

## Decisions (25 Sep 2026)

- **Identity.** ECI Files gets its own identity on the front page and in the charts. It shares the site
  header, type faces and trust colours.
- **Photos.** Official photos where rights-clear, initials otherwise. That's phase 4, not this phase.
- **State geography.** Equal-sized state tiles, never a geographic map.
- **Scope.** Phases 1 and 2 only.

## Phase 1 — shape the data

### 1a. Lanes (backend worker)

Each entry gets a `lane`, derived deterministically by the loader in `pipelines/curated/eci_files.py`. The first rule that matches wins:

| lane | rule |
| --- | --- |
| `responses` | `status == "response"` |
| `claims` | `status == "claim"` |
| `courts` | `"courts" in topics` or `kind == "case"` |
| `inside` | `"dissent" in topics` |
| `commission` | everything else |

- **Storage.** A new Alembic revision, `eci_files_lane_0005` in `0006_eci_files_lane.py`, adds `lane text NOT NULL DEFAULT 'commission'` with a CHECK on those five values, plus an index on `(lane, date)`.
- **Loader.** The loader computes the lane at load time. Data files never carry it.
- **Tests.** One test per rule, including precedence: a response tagged `courts` goes in `responses`.

### 1b. State figures (data shaper)

Write `data/eci_files/states.json`:

```json
{"states": [{"state": "Bihar", "phase": 1,
  "stages": [{"stage": "before|draft|final|appeals_filed|appeals_pending|restored", "electors": 78969844,
              "as_of": "2025-06-24", "source_entry": "<entry id>", "url": "<citation url>", "tier": 1}],
  "notes": "..."}]}
```

- **Where figures come from.** Only from entries in `data/eci_files/entries/numbers.json` (and other areas where a figure clearly belongs), taking each figure's own source.
- **No invented stages.** Where "before" must be computed, as draft plus left-out, record `"computed": true` and the method in `notes`.
- **The Stage model and loader.** Add an `EciStateStage` pydantic model and have the loader load this file into a new table, `eci_file_state_stage`: state, stage, electors bigint, as_of date, computed bool, source_entry_id text, url text, tier smallint. It's created in the same `0006` revision, and the load is a full replace like the rest.

### 1c. The objections (data shaper)

Write `data/eci_files/objections.json`: `{"objections": [{"n": 1, "date": "...", "date_precision": "...", "by": ["Sukhbir Singh Sandhu"], "concerns": "one neutral line", "entry_ids": ["..."], "followed_by": "what happened next, or null", "public": false}]}`.

- **Which objections.** The 14 formal objections the Indian Express reported, identified from the entries. List only what the record supports.
- **Keep the count honest.** If fewer than 14 can be identified, list those, and put a `"missing": <count>` field at the top level. Never invent one.
- **Not loaded yet.** It's used in phase 5.

### 1d. Duplicate merges (data shaper)

Write `data/eci_files/merges.json`: `{"merges": [{"keep": "<id>", "drop": ["<id>", ...], "reason": "same event: ..."}]}`.

- **What counts as a duplicate.** Pairs where two areas recorded the same real-world event, found by date plus people plus title similarity.
- **Which to keep.** The checked entry, else the one with a primary source.
- **Proposal only.** `scripts/eci_files_reconcile.py` applies it (backend worker): dropped ids get `exclude: true`, and their citations are appended to the kept entry, deduplicated by url.

### 1e. Courts (courts researcher)

- **What to write.** A new research area, `data/eci_files/research/courts.json`, in the BRIEF format.
- **What it covers.** Every Supreme Court and High Court case about the Commission, 2019 to today, as described in the brief. One `kind: "case"` entry per case, with parties, bench and case number in `details`, and one `kind: "event"` entry per order.
- **Avoid duplicates.** Read the existing `data/eci_files/entries/*.json` first and don't re-record orders already there. Reference their ids in `notes` instead.
- **Self-check as you go.** Every entry carries `"verification": {"verdict": "confirmed", "checked_url": "...", "note": "self-checked by researcher"}` only if you opened the source yourself. Otherwise mark it `unconfirmed`.

## Phase 2 — the front page, lane timeline and drawer

### API (backend worker)

- `GET /eci-files/summary` returns `{headline: [{value, label, source_label, source_url, entry_id}], key_moments: [EciEntry], counts: {entries, checked, people, citations}, last_loaded}`.
  - **Headline.** The four stats come from a small curated file, `data/eci_files/headline.json`, loaded into a table `eci_file_headline(position, value, label, source_label, source_url, entry_id)`. Seed it with the four in the redesign plan, taking values and sources from the matching entries. Every number needs a source.
  - **Key moments.** Entries whose id is listed in `headline.json` under `"key_moments"`: about 8 ids picked from the entries covering 2023 Act, the appointments, the SIR start, key court orders, the objections, and the ECI response.
- `GET /eci-files/timeline` gains:
  - `lane=`;
  - `from=`/`to=` windows. These already exist; the web asks for about 6 months at a time;
  - `fields=compact`, which returns only `id, date, date_precision, title, status, lane, check_status, people` (without citations) for drawing dots;
  - a `lanes: [{lane, count}]` facet.
- `GET /eci-files/density` returns `{months: [{month: "2025-08", lane, count}]}` for the overview strip.

### Web (web worker)

- **`/eci-files` becomes the front page:**
  1. A short hero: the one-line thesis and the four headline stats, each with a tappable source.
  2. "Start here" question cards linking to filtered views: timeline by lane or topic, and people.
  3. A "key moments" strip of about 8 entries, horizontal, on one axis.
  4. An entry into the timeline.
- **`/eci-files/timeline`: the lane timeline.**
  - **Overview.** A density strip across 2019 to 2026 by month. Brushing or clicking a range sets the window.
  - **Lanes.** Five lanes for the window: Commission, Inside the Commission, Courts, Claims, Responses. Dots sit at their real dates, coloured by status with the same four trust colours. A checked entry has a solid dot; an unchecked one is hollow.
  - **Drawer.** Clicking a dot opens it (a side panel on desktop, a bottom sheet on mobile) with the full entry: title, date, status, attribution, summary, people, responses and citations. It deep-links via `?entry=<id>`.
  - **Filters** for lane, topic and person sit in one row above, without losing the current window.
  - **On phones** (under 640px), the lanes collapse to a vertical card stream for the window, with the same drawer.
  - **Loading.** Fetch `fields=compact` for the dots and the full entry for the drawer. The first paint must not load the whole record.
- **The old long list** stays reachable at `/eci-files/entries` as the "deep dive". It is the current timeline component, paginated by year.
- **Identity.**
  - Add ECI-specific role tokens to `globals.css` for both themes: `--eci-ink` (the section accent, an indelible-ink violet), and `--eci-doc`, `--eci-report`, `--eci-claim`, `--eci-response`.
  - The trust colours, validated for colour-blind safety, are:
    - light: `#2a78d6`, `#eb6834`, `#1baf7a`, `#eda100`;
    - dark: `#3987e5`, `#d95926`, `#199e70`, `#c98500`.
  - Components use only those tokens. The light aqua and yellow are under 3:1 contrast, so dots always come with a legend, and the drawer shows the status as text.
- **Charts** are hand-built SVG React components, like `components/resume/charts.tsx`. No new charting library.
- **Accessibility.** Dots are buttons with an aria-label of date, title and status. The keyboard moves between dots within a lane, and Esc closes the drawer.
- **Unchanged from before.** Still noindex, still not in the sitemap, still unlinked. `npm run lint`, `typecheck` and `build` must pass, and the build must not need the API.
