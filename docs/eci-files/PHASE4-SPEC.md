# ECI Files redesign: phase 4 (people) spec

This is the build contract for phase 4. Read `SPEC.md` and `REDESIGN-SPEC.md` first, because this phase builds
on both. The stance rules in `data/eci_files/research/BRIEF.md` still apply. For this phase the key one is:
**profiles are public-service records only.** That means postings, roles and documented actions. No family,
home, health or personal-life details.

The problem this phase fixes: `/eci-files/people` is an alphabetical grid of 86 names, where a Chief Election
Commissioner and a lawyer named once look the same. `/eci-files/people/[slug]` is a block of text followed by
a long list. The owner found both unintuitive. The bar is an ICIJ Offshore Leaks entity page, a LittleSis
profile or a ProPublica explainer. Each should answer "who is this, what power did they hold, who put them
there, and what does the record say they did" in that order, with a source one tap away.

## Decisions already made (owner, 25 Sep 2026)

- **Photos.** Official photos where rights-clear, initials otherwise. See §4.
- **Identity.** ECI Files keeps its own identity: the `--eci-ink` accent and the four trust tokens.
- **Launch.** Every page stays hidden: `noindex`, out of `sitemap.ts`, not linked from `SiteHeader` or the homepage.

## What already exists (read before changing)

| Layer | File | Today |
| --- | --- | --- |
| data | `data/eci_files/entries/commissioners.json`, `officials.json` | 30 `kind:"person"` entries (9 commissioners, 21 officials). `details` has `role, tenure[], service, career[], selection, selection_source_url, education, tenure_end`, and on 5 entries `born`. |
| data | `data/eci_files/entries/selection-law.json`, `commissioners.json`, `statements-reporting.json` | Selection events and dissents. Several selection-law entries are `exclude:true` after `merges.json`, so the kept ids live in `commissioners.json`. |
| data | `data/eci_files/selections.json` (**new, written for this phase**) | 3 regimes, 8 selections (2019–2025), 6 departures. Every member and dissent cites loaded entry ids. |
| data | `data/eci_files/people_media.json` (**new, written for this phase**) | 9 commissioner photos with licence, attribution and crop. |
| loader | `ingestion/neta_ingest/pipelines/curated/eci_files.py` | Full replace of `eci_file_entry/person/entry_person/citation`, plus `state_stage`, `headline` and `key_moment` from optional files. |
| storage | `backend/database/migrations/versions/0005_eci_files.py`, `0006_eci_files_lane.py` | Revision ids `eci_files_0004` and `eci_files_lane_0005`. |
| api | `api/neta_api/services/eci_files.py` (`people`, `person_page`), `routers/eci_files.py`, `schemas.py` | `EciPersonSummary {slug,name,role,tenure,entry_count}`, `EciPersonPage {person:{slug,name,profile}, entries}` |
| web | `web/src/app/eci-files/people/page.tsx`, `people/[slug]/page.tsx`, `components/eci-files/PersonCard.tsx`, `LaneTimeline.tsx`, `EntryDrawer.tsx`, `EntryDetail.tsx`, `lib/eci-files.ts`, `types/eci-files.ts`, `lib/api.ts`, `app/globals.css` | Card grid, text profile, lane timeline with a `?entry=` drawer |

Two defects in what exists. Both get fixed in this phase:

1. **The profile prints the date of birth.** The generic `detailLines()` renders every scalar in `details`, so
   5 profiles show `born`. Profiles must not render `born`. §2.4 replaces the generic helper with an allowlist.
2. **Two people share one slug.** Justice Sanjay Kumar (Supreme Court) and Deputy Election Commissioner
   Sanjay Kumar both slug to `sanjay-kumar`, so the CJI-recusal entry `selection-law-cji-khanna-recuses`
   shows up on the DEC's profile. Fix it in the data: in `data/eci_files/entries/selection-law.json`, change
   that one entry's `people` value `"Sanjay Kumar"` to `"Justice Sanjay Kumar"`. The judge becomes
   `justice-sanjay-kumar`. No other entry names the judge. (Open question 4 asks about naming judges
   consistently.)

---

## 1. `/eci-files/people`: the index

### 1.1 Page order (top to bottom)

1. **`SectionHero`**
   - eyebrow `ECI FILES · PEOPLE`
   - title `Who runs the Election Commission`
   - subtitle: `The commissioners, the officials under them and the state officers who run the rolls, 2019 to today. Every line has a source.`
   - `backHref="/eci-files"`
2. **Section nav**: one row of anchor chips with counts, as `<nav aria-label="Groups on this page">`:
   `The Commission 9 · Senior officials 10 · State election officers 11 · Also named 57`. Counts come from the data, not fixed.
3. **"Who ran the Commission"**: the tenure chart (§1.2), full width, with the caption and legend.
4. **The Commission** (`id="commission"`): 9 large cards (§1.3), ordered as in §1.4.
5. **Senior officials at the Commission** (`id="secretariat"`): medium cards.
6. **State Chief Electoral Officers** (`id="state"`): compact rows.
7. **Also named in the record** (`id="named"`): a compact multi-column list.
8. **Photo credits**: a `<details>` footnote listing each photo's attribution line, linked to its `source_page` and licence (§4.3).
9. A footer link row: `How they were chosen →` (`/eci-files/selections`), then `← Every entry` (`/eci-files/entries`).

Each group heading is an `h2` with a one-line description under it:

| id | h2 | description |
| --- | --- | --- |
| `commission` | The Commission | Chief Election Commissioners and Election Commissioners who served between 2019 and today. |
| `secretariat` | Senior officials at the Commission | Deputy and senior deputy election commissioners, the Director General (IT), the Commission's secretaries and its observers. |
| `state` | State Chief Electoral Officers | The officers who run the rolls and elections in each state, where the record names them. |
| `named` | Also named in the record | Judges, lawyers, ministers and party leaders who appear in entries. They have no profile here. Each page lists the entries that name them. |

### 1.2 `CommissionTenureChart`: "Who ran the Commission"

Build it as hand-built SVG in `web/src/components/eci-files/CommissionTenureChart.tsx`. Model it on the SVG in
`components/eci-files/DensityStrip.tsx` and `LaneTimeline.tsx`. Do not model it on `components/resume/charts.tsx`,
which imports Recharts. No chart library. Wrap it in a `<figure>` with a `<figcaption>`.

- **Data.** The `commission` group from `GET /eci-files/people`, taking each person's `tenure[]`.
- **Axis.**
  - `ECI_TENURE_AXIS = { from: "2019-01-01", to: <today, ISO> }`, exported from `lib/eci-files.ts`. Every tenure bar on every page uses it.
  - Year ticks every Jan 1, labelled `2019`…`2026` (`'19`…`'26` under 640px).
- **Rows.**
  - One row per commissioner, in `group_rank` order (chronological by first appointment).
  - Label column: 148px on desktop. Under 640px the name sits above the bar instead.
  - Each row is an `<a href="/eci-files/people/{slug}">` wrapping the label and the bars.
  - Row height is 26px.
- **Bars.** One rounded rect per tenure segment.
  - Election Commissioner: fill `color-mix(in srgb, var(--eci-ink) 32%, var(--card))`, with a 1px `var(--eci-ink)` stroke.
  - Chief Election Commissioner: fill `var(--eci-ink)`.
  - A segment that starts before the axis is clipped at the left edge. It gets a small `◂` glyph and the text `from Sep 2017` in `--faint`, 10px.
  - A segment with `to: null` runs to today and ends in a small open-ended notch (no rounded right corner).
- **Markers.** Vertical lines across all rows, with labels at the top:
  - 2 Mar 2023: dashed `--faint`, labelled `Court's interim rule`.
  - 2 Jan 2024: solid `--eci-ink`, labelled `2023 Act in force`.
  - Both labels link to the regime cards on `/eci-files/selections#regimes`.
- **Selection ticks.** For each selection in `GET /eci-files/selections`, draw a 7px diamond on each appointee's row at the selection date, filled `--eci-ink`.
  - A selection with a dissent gets a hollow diamond plus a 2px ring.
  - Each diamond is an `<a href="/eci-files/selections#{selection.id}">` with an aria-label like `Selected 14 Mar 2024 under the 2023 Act, one dissent recorded`.
- **"Members in office" strip.** A 14px step strip under the rows. It counts the commissioners in office each day (0–3), computed from the tenures.
  - Shade: 3 = `color-mix(... --eci-ink 12%)`, 2 = 24%, 1 = 45%.
  - Label on the left: `Members in office`.
  - This is what shows the May–Nov 2022 vacancy and the one-member Commission of 9–15 Mar 2024 without any extra copy.
  - Hovering or focusing a run shows `2 members, 15 May – 20 Nov 2022`.
- **Legend.** Placed above the chart: `▭ Election Commissioner ▬ Chief Election Commissioner ◆ Selection ◇ Selection with a recorded dissent`.
- **Caption.** `Tenures from each commissioner's profile entry. The 2023 Act moved selection to a committee of the Prime Minister, a minister he nominates and the Leader of Opposition.` Follow it with a `How they were chosen →` link.
- **Accessible alternative.** A `<details><summary>Show as a table</summary>` with a real `<table>`. Columns: Name, Office, From, To. One row per segment.

### 1.3 Cards

**`PersonCard` (rewrite of `components/eci-files/PersonCard.tsx`)**, for the `commission` and `secretariat` groups. The whole card is one link. Contents:

- `PersonAvatar` (§2.6) on the left: 64px for the commission group, 48px for the secretariat group.
- Name: serif, 17px, `--ink`.
- Role line: `details.role`, 12.5px, `--ink2`.
- Status chip:
  - `Serving` when `current`. Chip bg is `color-mix(in srgb, var(--eci-ink) 12%, var(--card2))` and text is `--eci-ink`.
  - Otherwise `Former`, in the `--muted` style.
  - When there are no tenure dates at all, no chip.
- `TenureBar` (§2.5) on the shared axis: 8px high, full card width. Commission cards only. Secretariat cards show the tenure text line instead (`formatTenure`).
- Entries line: `StatusCountBar` (a 4px stacked bar of the four trust tokens, width proportional to counts), then mono text `70 entries · 11 documented · 24 reported · 23 claims · 12 responses`. Zero counts are omitted. The text is what carries the information; the bar only echoes it.
- Service: `details.service`, 11.5px, `--muted`, one line with ellipsis. The full text goes in `title`.

**`StateOfficerRow`**, for the `state` group. One row per officer, laid out as a table (`<table>` with a caption, not divs):

- Columns: State · Name (link) · In office · Entries.
- "In office" uses `formatTenure`, e.g. `Mar 2025 – May 2026` or `since Jun 2025`.
- Sorted as in §1.4.
- Under 640px each row becomes two lines: state and dates on top, then name and entries.

**`NamedPeopleList`**, for the `named` group. A CSS multi-column list (`columns: 3 200px`). Each item is a link: name, then the entry count in mono `--faint`. Alphabetical by name.

### 1.4 Grouping and order (derived by the loader, §5.2)

| group | rule, applied to the profile entry's `details.tenure[].office` (first match wins) | order within group |
| --- | --- | --- |
| `commission` | any office fully matches `^(Chief )?Election Commissioner$` | earliest `tenure.from` ascending, then name |
| `state` | any office starts with `Chief Electoral Officer` | state name (text after `Chief Electoral Officer, `), then serving first, then start date descending |
| `secretariat` | any office matches `Deputy Election Commissioner\|Director General\|Secretary\|Observer`, **or** the person has a profile and matched nothing above | office rank (0 Deputy / Senior Deputy EC, 1 Director General, 2 Principal Secretary / Secretary, 3 Observer, 4 other), then serving first, then start date descending (nulls last), then name |
| `named` | no profile entry | name |

- **`current`** is true when any tenure has `from` set and `to` null. Profiles with neither date (Pramod Kumar Sharma, Pawan Diwan, Nitesh Kumar Vyas) are not current, and render `Dates not on record`.
- **Expected result on today's data.**
  - Commission: Arora, Lavasa, Chandra, Rajiv Kumar, Pandey, Goel, Gyanesh Kumar, Sandhu, Joshi.
  - The loader test asserts this order against a fixture built from the same rule (§5.6).

---

## 2. `/eci-files/people/[slug]`: the profile

### 2.1 Layout

The page is a single column, `maxWidth 1080`. At ≥960px there is a right rail (300px) that holds the "Selected by" block and key facts. Under 960px everything stacks in the order below.

1. **`ProfileHeader`**
   - `PersonAvatar` at 112px (72px under 640px).
   - Under the avatar, the photo credit in 10.5px `--faint`: `Photo: PIB / ECI · GODL-India`, linked to `photo.source_page`.
   - The `h1` name, serif, `clamp(26px, 4vw, 34px)`.
   - The role line (`details.role`).
   - A chip row: group label (`The Commission`, `Senior official`, `State election officer`), `Serving` or `Former`.
   - The service line (`details.service`), rendered verbatim.
   - The breadcrumb `← People`.
2. **`TenureBar`** at 14px on the shared axis `ECI_TENURE_AXIS`, with year ticks. The office labels sit inside or above each segment: `EC Mar 2024 – Feb 2025`, then `CEC since Feb 2025`.
   - Under it, `details.tenure_end` in 12.5px `--muted` if present.
   - With no dates, the text `Tenure dates not on record` goes in place of the bar.
3. **`KeyFacts`** (§2.3): a row of 4 tiles, laid out 2×2 under 640px.
4. **Section nav**: `<nav aria-label="On this page">` with anchor chips. It shows only the sections that exist, each with a count:
   `Career 10 · Selected by · Timeline 70 · Decisions & objections 34 · Mentions 24 · Responses 12 · Sources 9`.
5. **`CareerTimeline`** (§2.4), `id="career"`.
6. **`SelectedByBlock`** (§2.5.1), `id="selected-by"`. It goes in the right rail on desktop and after Career on mobile. For people who sat on panels, `PanelSeatsBlock` comes instead (§2.5.2).
7. **Timeline** (`id="timeline"`): `LaneTimeline` fed with this person's entries (§2.6), plus `StatusLegend` and the `?entry=` drawer.
8. **Three entry sections** (§2.7), each an `h2` with a count, showing entry cards newest first:
   - `Decisions & objections` (`id="decisions"`)
   - `Mentions` (`id="mentions"`)
   - `Responses` (`id="responses"`)
9. **Sources for this profile** (`id="sources"`): `CitationList` of `profile.citations`.

Hierarchy rule: the only serif sizes on the page are h1 34, h2 20 and card titles 15. Mono is used only for dates, counts and eyebrows.

### 2.2 People with little or no data

- **Profile but almost empty** (e.g. `pramod-kumar-sharma`: 1 career line, no dates, 4 entries):
  - The header renders with initials.
  - `TenureBar` is replaced by `Tenure dates not on record`.
  - KeyFacts shows only the tiles that have a value.
  - The Career section shows the one line.
  - Sections with zero entries are **left out of the page and the nav**. They are not rendered empty.
  - Under the header, add one line in `--muted`: `The record has little on {name} so far: {n} entries and {c} career lines.` It shows only when entries < 5 and career lines ≤ 1.
- **No profile** (the `named` group, e.g. `rahul-gandhi`):
  - Header: initials, name, and the chip `Named in the record`.
  - The line `No profile: this page lists the {n} entries that name {name}.`
  - Then `PanelSeatsBlock` if they sat on a selection panel, then the Timeline and the three sections.
  - No KeyFacts, no Career.
- **Missing values** render `—`, never `0` or an empty string. This is the house rule.

### 2.3 `KeyFacts`

The tile shape: an eyebrow in mono 9.5px `--faint` uppercase, a value in 18px/600 `--ink`, and one line of context in 11.5px `--muted`. At most 4 tiles; a tile with no value is dropped.

| Group | Tile 1 | Tile 2 | Tile 3 | Tile 4 |
| --- | --- | --- | --- | --- |
| commission | **Time at the Commission**: the sum of the tenure spans with `from` set, up to today, as `6 yr 6 mo`. Context: `EC 11 mo · CEC 7 mo…` per office. | **Selected under**: the regime label of their most recent appointment (`2023 Act committee`, `Executive convention`). Context: the date. Links to `#selected-by`. Without a selection row (Arora, Lavasa, appointed before 2019): `Executive convention`, context `appointed before 2019`, taken from the regime whose window contains the first tenure date. | **Dissent at selection**: `1 recorded` / `None recorded`. Context: who dissented. Shown only if a selection row exists. | **Entries on record**: count, plus `StatusCountBar`. |
| secretariat, state | **Office**: the latest tenure office. | **In office**: `formatTenure` of the latest tenure, or `—`. | **Service**: `details.service` (value 14px, may wrap). | **Entries on record**. |

### 2.4 `CareerTimeline`

Put it in `web/src/components/eci-files/CareerTimeline.tsx`. The data comes from a pure helper `careerTimeline(details, tenure)` in `lib/eci-files.ts`:

```ts
interface CareerItem {
  post: string;
  from: string | null; to: string | null;          // as in the data ("2019", "2019-08", "2019-08-01")
  label: string;                                    // see rules below
  sources: { url: string; kind: "official" | "court" | "press"; host: string }[];  // source_url then additional_source_url
  atCommission: boolean;                            // post names ECI / Election Commission / Chief Electoral Officer
}
function careerTimeline(details, tenure): { dated: CareerItem[]; undated: CareerItem[] }
```

- **Sort key.** `from ?? to`. Items with neither go to `undated`, keeping the source order. `dated` is sorted ascending, oldest first, because this is the path to the office.
- **Labels.**
  - Both dates: `1985 – 1993` / `Apr 2021 – May 2022`, via `formatLooseDate`.
  - Only `to`: `until 2006`.
  - Only `from`, and the post matches a tenure office whose `to` is null (case-insensitive substring match on the office): `since Feb 2025`.
  - Only `from` otherwise: `from 2012 · end date not in source`. **Do not print "present"**, because a null `to` in `career` means unknown, not ongoing.
- **`sourceKind(url)`.**
  - Host ends in `gov.in` or `nic.in` → `official`, labelled `Official record`.
  - `indiankanoon.org`, `scobserver.in` or `sci.gov.in` → `court`, labelled `Court record`.
  - Anything else → `press`, labelled `Press report`.
- **Render.**
  - An `<ol>` with a 2px vertical rail on the left.
  - Items where `atCommission` is true get a `--eci-ink` rail segment and dot. All other items get `--rule2`.
  - Desktop has a 132px date column. Under 640px the date sits above the post.
  - Each source is a small link chip: `eci.gov.in ↗ Official record`. `rel="noopener noreferrer"`, `target="_blank"`.
  - Then, if `undated` is non-empty, a sub-heading `Postings listed without dates` and the note `The source lists these without dates. They appear in the source's order.` The same item style follows, without a date column.
- **Allowlist for profile facts** (replaces `detailLines()` on this page):
  - Allowed: `service`, `education` and `tenure_end`.
  - `role`, `tenure`, `career` and `selection*` have their own blocks.
  - **`born` and any other key are never rendered.** Delete `detailLines` if nothing else uses it.

### 2.5 `TenureBar` and the selection blocks

`TenureBar({ tenure, axis = ECI_TENURE_AXIS, height, showLabels })` goes in `components/eci-files/TenureBar.tsx`.

- It shares its segment geometry with the chart through `tenureSegments(tenure, axis)` in `lib/eci-files.ts`, which returns `{office, kind: "ec"|"cec"|"other", x0, x1, clippedStart, openEnd}`.
- `other` offices (DEC, CEO, DG) use fill `color-mix(in srgb, var(--ink2) 28%, var(--card))`.
- A tenure with only `to` draws a 2px tick at `to` with the label `until May 2026`.
- It is `role="img"`, with an aria-label built from `formatTenure`.

#### 2.5.1 `SelectedByBlock`

The source is `person_page.selections` where this person is an appointee. One card per selection, newest first.

- **Eyebrow and title.** Eyebrow `SELECTED BY`. Title, e.g., `Chief Election Commissioner · 17 Feb 2025`.
- **Regime chip.** `2023 Act committee` / `Executive convention`, linking to `/eci-files/selections#regime-{key}`.
- **Panel list.** One line per member: avatar at 24px, name linked if `has_profile` or `person_slug`, role in `--muted`, and a part badge.
  - Part badges: `Chair`, `Proposed`, `Majority`, `Dissented`, `Recommended`.
  - `Dissented` uses the `claim` token styling (the dissent entries are claims) and always carries the text, not only the colour.
  - A role-only member (`person_slug: null`) shows the role text alone, with no link.
  - Convention selections: `Appointed by the President on the Union government's advice. No committee existed.` The member line appears only if one is recorded (Goel: `Prime Minister · Recommended`).
- **Search committee** (when `search` is present). Show `by`, the shortlist size, and the shortlist names as plain text (not links).
  - When the shortlist is shown, always add the provenance line in `--muted`: `Shortlist from Adhir Ranjan Chowdhury's account to The Indian Express. The minutes are not public.` The text comes from `search.shortlist_source`. Do not hard-code it.
- **Dissent.** A bordered sub-card with the `StatusChip` for `dissent.status` (`Claim`), the summary, `Note published: yes/no`, and a `Response:` link to each `response_entry_ids` entry title.
- **Notes.** `selection.notes`, if present, in 12.5px `--muted`.
- **Cited entries.** A mono line `Cited: ` listing each of `entry_ids` as its entry title (from `entries_index`, §5.4). Each opens the drawer on this page via `?entry=`.
- **Fallback with no selection rows.** Render `details.selection` as a paragraph, labelled `From the profile`, with a `source ↗` link to `details.selection_source_url`.

#### 2.5.2 `PanelSeatsBlock`

Used for Modi, Shah, Chowdhury, Gandhi and Meghwal. It shows the selections where the person's `part` is not `appointed`.

- Eyebrow `SAT ON SELECTION PANELS`.
- One line per selection: date, `selected {appointee names}`, role, and part badge.
- Each line links to `/eci-files/selections#{id}`.
- For `search_chair` the line is `Chaired the search committee`.

### 2.6 The person's lane timeline (reuse `LaneTimeline`)

- **Input.** The page's `entries` (full `EciEntry[]` are structurally compatible with `EciCompactEntry`).
- **Window.**
  - `from` = max(`2019-01-01`, the first day of the month of the earliest entry date).
  - `to` = today.
  - If `from` is within 60 days of `to`, set `from` 6 months earlier.
- **New prop `hideEmptyLanes?: boolean`** (default `false`, so `/eci-files/timeline` is unchanged). The profile passes `true`.
- **Drawer.** The profile reads `searchParams.entry`.
  - If the id is in `entries`, render `<EntryDrawer><EntryDetail entry={...} basePath={/eci-files/people/{slug}} /></EntryDrawer>` without a fetch.
  - Otherwise, e.g. a selection-cited entry that doesn't name this person, fetch it with `getEciEntry`.
- **`eciEntryHref(id, preserve, basePath = "/eci-files/timeline")`** gains a `basePath` argument, and `EntryDetail` gains an optional `basePath` prop passed through to it. Existing callers are unchanged.

### 2.7 The three entry sections

The split is deterministic, from the entry's `lane` (redesign spec 1a):

| Section | lanes | Intro line |
| --- | --- | --- |
| Decisions & objections | `commission`, `inside` | What the Commission did while {name} served, and objections recorded inside it that name {name}. |
| Mentions | `courts`, `claims` | Court proceedings and claims by others that name {name}. |
| Responses | `responses` | Answers on the record from {name}, the Commission or the government. |

- **Cards.** Each section lists `EntryCard`s (the existing component), newest first. Each card links to `?entry=` so the drawer opens.
- **Paging.** Show 8, then a `Show all {n}` button that expands in place. It is a client component; no refetch.
- **Empty sections** are not rendered (§2.2).
- **Profile entry.** The profile's own `kind:"person"` entry is excluded from all three sections. The timeline query already drops `kind = 'person'`, so apply the same filter to `person_page.entries` in the service.

---

## 3. `/eci-files/selections`: how they were chosen

This is a new route: `web/src/app/eci-files/selections/page.tsx`. It gets `robots: {index:false, follow:false}`, stays out of the sitemap, and is linked only from the people page and from profiles.

1. **`SectionHero`**
   - eyebrow `ECI FILES · SELECTIONS`
   - title `How the commissioners were chosen`
   - subtitle `Eight selections from 2019 to 2025, who sat on each panel, and the two recorded dissents. Every line cites an entry.`
2. **`RegimeCompare`** (`id="regimes"`): three cards side by side, stacked under 720px.
   - Each card has `id="regime-{key}"` and shows the label, the date range, `rule`, and the `panel` as a list.
   - A 3-seat diagram is drawn in SVG: 3 circles.
     - Convention: 1 filled circle labelled `Government`, plus the text `No committee`.
     - Court's interim rule: 3 circles, `PM · LoP · CJI`, 1 government seat.
     - 2023 Act: `PM · PM's minister · LoP`, with the 2 government seats filled `--eci-ink` and the LoP hollow.
   - Under the diagram: `{n} selections made under this rule`. The Court's interim card also shows the regime `notes`: `No appointment is recorded…`.
   - Each card ends with `Cited:` entry links.
   - Seat fill encodes "chosen by the government", and the seat labels say so in text as well.
3. **`SelectionGraph`** (`id="network"`): a bipartite node-link view, rendered at ≥720px. Hand-built SVG.
   - **Left column (selectors), top to bottom:**
     1. The role node `Union government (convention)`.
     2. The role node `Prime Minister` (the Goel recommendation, `person_slug: null`).
     3. Narendra Modi, Amit Shah, Adhir Ranjan Chowdhury, Rahul Gandhi.
   - **Right column (appointees):** one node per appointment, in date order. Gyanesh Kumar appears twice (EC 2024, CEC 2025), which is the point. Each node is labelled `Name · EC · Mar 2024`.
   - **Regime bands.** Light horizontal bands behind the right column group appointments by regime, with the regime label at the band's right edge.
   - **Edges.** One per (member, appointee) pair in a selection. Convention selections with no recorded member draw one edge from `Union government (convention)`.
   - **Edge styles:**

     | part | stroke |
     | --- | --- |
     | `voted_with_majority` | 1.5px `--eci-ink` |
     | `proposed` | 3px `--eci-ink` |
     | `recommended` | 1.5px dashed `--eci-ink` |
     | `dissented` | 1.5px dashed `--eci-claim`, with an `×` glyph at the midpoint |
     | convention | 1px `--rule` |

   - **Interaction.**
     - Hovering or focusing a node highlights its edges and dims the others to 25% opacity.
     - Each node is an `<a>`: people to their profile, role nodes to `#regimes`.
     - Each edge has a transparent 12px-wide hit path, wrapped in `<a href="#{selection.id}">`.
     - The tooltip reads, e.g., `Adhir Ranjan Chowdhury dissented · selection of 14 Mar 2024 · cites commissioners-event-2024-03-14-chowdhury-dissent`.
   - **Every edge maps to at least one entry id.** The edge's citation is the member's `entry_ids` (the convention edge uses the selection's `entry_ids`). The component asserts this with a dev-only `console.error` when an edge has none.
   - **Accessibility.** The SVG is `role="img"` with `aria-labelledby` a hidden summary (`8 selections…`) and `aria-describedby="selection-list"`. The list below is the accessible form.
   - **Under 720px** the graph is not rendered. The list below carries everything.
4. **`SelectionList`** (`id="selection-list"`): one `SelectionCard` per selection, newest first, each with `id={selection.id}`. It is the same card as `SelectedByBlock` with the appointees added as avatar and name links at the top.
5. **Departures** (`id="departures"`): a small table (Date · Name · Office · How it ended · Cited).
   - `how` renders `Resigned` / `Tenure ended`.
   - Goel's row carries its note: `Left the Chief Election Commissioner as the only member until 15 Mar 2024.`
6. **Gaps**: the file's `gaps[]` under `What the record doesn't show`, as a bulleted list in `--muted`.
7. **Drawer.** `?entry=` opens `EntryDrawer` with `getEciEntry` and `basePath="/eci-files/selections"`.

**Copy rules.** Everything is neutral and taken from `selections.json`. Do not add words like "rushed" or "packed". Speed appears only as dates, and the court's remarks appear only through the cited entries.

---

## 4. Photos

### 4.1 Findings

I checked each candidate on 25 Sep 2026 through the Wikimedia Commons API (file page, source, licence tag and review status) and on eci.gov.in.

- **eci.gov.in itself.** Photos exist:
  - Current members: `/newimg/cec_shri_gyanesh_kumar_img.jpg`, `Dr-Sukhbir-Singh-Sandhu.jpg` and `dr-vivek-joshi.jpg`. These are 1924×401 banners with text baked in.
  - Former members: `/newimg/former-cec-ec/mr-sunil-arora.png`, `sh-ashok-lavasa.png`, `mr-sushil-chandra.png`, `shri-rajiv-kumar.png`, `shri_ACP.png` and `shri_AG.png`. These are portraits in a decorative frame with the ECI logo.
  - The site footer says `© Copyright Election Commission of India 2026`. No open licence or reproduction policy is published in the site bundle. The only terms text found is ECINET's ("exclusive property of the ECI").
  - **Not rights-clear. Not used, not hotlinked.**
- **PIB.** pib.gov.in's copyright/website-policy page returned "page not available", and there is no Wayback copy, so I could not verify PIB's own terms this session. PIB photos are used here **through Wikimedia Commons**, where each is tagged `GODL-India`, and for five of them a Commons reviewer or bot has confirmed the tag against the PIB source.
- **GODL-India** grants a "worldwide, royalty-free, non-exclusive license to use, adapt, publish… display… and create derivative works… for all lawful commercial and non-commercial purposes". The condition is that the user acknowledges the provider, source and licence. **That permits self-hosting and cropping, with attribution.** Its exclusions include official names, crests and logos. So crop the photos to the face, keep the State Emblem out of the frame where possible, and never use the emblem as a graphic.

| Person | File (Commons) | Original source | Licence review | Decision |
| --- | --- | --- | --- | --- |
| Gyanesh Kumar | `The Chief Election Commissioner of India, Sh. Gyanesh Kumar.jpg` (869×840, 25 Jun 2025) | PIB photo 186266 | confirmed (Commons reviewer, 26 Mar 2026) | self-host |
| Sukhbir Singh Sandhu | `Election Commissioner Shri Sukhbir Singh Sandhu.jpg` (352×373, 22 Apr 2024) | PIB photo 157812 | confirmed | self-host |
| Rajiv Kumar | `Chief Election Commissioner of India Rajiv Kumar (cropped).jpg` (447×559, 26 Feb 2024) | PIB photo 154850 | confirmed | self-host |
| Arun Goel | `Election Commissioner Arun Goel.jpg` (1156×1346, 26 Feb 2024) | PIB photo 154852 | confirmed | self-host |
| Ashok Lavasa | `Shri Ashok Lavasa taking charge as the New Election Commissioner… January 23, 2018.jpg` (2200×1920) | PIB photo 120886 | confirmed (bot) | self-host, cropped to face |
| Sunil Arora | `Media address by Chief Election Commissioner of India, Shri Sunil Arora on 2nd December 2018 (cropped).jpg` | eci.gov.in gallery | uploader-asserted | self-host, subject to Open question 1 |
| Sushil Chandra | `Sushil Chandra, Election Commissioner of India (cropped).jpg` (311×350) | eci.gov.in banner | uploader-asserted | self-host, subject to Open question 1 |
| Anup Chandra Pandey | `Shri Anup Chandra Pandey.jpg` (200×200) | eci.gov.in profile | uploader-asserted | self-host, subject to Open question 1 |
| Vivek Joshi | `Vivek Joshi IAS CEC.jpg` (524×400) | eci.gov.in profile | uploader-asserted | self-host, subject to Open question 1 |
| 14 senior officials and CEOs | nothing openly licensed found on Commons | — | — | initials |

I rejected a CC0 "own work" crop of Gyanesh Kumar and a CC BY-SA 2018 Kolkata photo of Arun Goel in favour of PIB originals, so that official provenance is consistent across all nine.

Everything above is recorded in `data/eci_files/people_media.json`: `slug, name, image_url, source_page, original_source, original_publisher, caption, photo_date, licence, licence_url, licence_review, attribution, self_host, local_path, crop{cx,cy,size}, original_size`. The crop hints were checked visually.

### 4.2 Self-hosting (backend worker)

Write `scripts/eci_files_fetch_photos.py`, run as `uv run --with pillow python scripts/eci_files_fetch_photos.py [--force]`:

1. Read `data/eci_files/people_media.json` and take each `self_host: true` item.
2. Download `image_url` with `User-Agent: neta-resume/1.0 (+https://github.com/...; editorial)`. Timeout 60s, 1 retry.
3. Crop a square: side = `size × min(w,h)`, centred at `(cx·w, cy·h)`, clamped inside the image.
4. Resize to 480×480 (Lanczos). Never upscale: if the side is under 480, keep the native size. Pandey is 200, Chandra 311, Sandhu 352.
5. Save as progressive JPEG, quality 84, EXIF stripped, to `web/public/eci-files/people/{slug}.jpg`.
6. Skip existing files unless `--force`. Print one line per file (`slug  WxH  bytes`).

Commit the 9 JPEGs (each under 90 KB). Nothing fetches at request time. There is no image proxy and no `next/image` remote pattern, just `<img src="/eci-files/people/{slug}.jpg">`.

### 4.3 Attribution (web worker)

- **Profile.** A caption under the avatar: `Photo: {short credit} · GODL-India`. The short credit is `PIB / ECI` when `original_publisher` starts with `Press Information Bureau`, else `ECI`. The whole caption links to `source_page`, and `GODL-India` links to `licence_url`. The full `attribution` string goes in the link's `title`.
- **People page footnote.** `<details><summary>Photo credits</summary>` lists every `attribution` line with links to `source_page` and `licence_url`, plus `People without a photo are shown with initials.`
- **Cards and avatars under 64px** carry no caption. The footnote covers them.

---

## 5. Backend: storage, loader, API

### 5.1 Alembic revision

- **File:** `backend/database/migrations/versions/0008_eci_files_people.py`
- **Revision id:** `eci_files_people_0007`
- **`down_revision`:** `"eci_files_states_0006"`, phase 3's revision in `0007_eci_files_states.py` (see `PHASE3-SPEC.md` §1.5). If phase 3 has not merged when you start, branch from it or temporarily point at `eci_files_lane_0005` and re-point before merge. Say which in the PR description.
- **Coordination with phase 3.** Phase 3 also edits the loader's delete and insert order in `_replace_all` (regions, states, national figures). Rebase onto phase 3 before touching `_replace_all`. Your deletes go first and your inserts go last, after phase 3's.

```
ALTER eci_file_person ADD
  role_group   text NOT NULL DEFAULT 'named' CHECK (role_group IN ('commission','secretariat','state','named'))
  group_rank   integer NOT NULL DEFAULT 0
  is_current   boolean NOT NULL DEFAULT false
  first_from   date            -- earliest tenure.from (partial dates -> first day)
  last_to      date            -- latest tenure.to
  INDEX (role_group, group_rank)

eci_file_person_media
  person_slug      text PRIMARY KEY REFERENCES eci_file_person(slug) ON DELETE CASCADE
  url              text NOT NULL        -- local_path when self_host, else image_url
  image_url        text NOT NULL
  source_page      text NOT NULL
  original_source  text
  original_publisher text
  caption          text
  photo_date       date
  licence          text NOT NULL
  licence_url      text NOT NULL
  licence_review   text NOT NULL CHECK (licence_review IN ('reviewed','uploader_asserted'))
  attribution      text NOT NULL
  self_host        boolean NOT NULL

eci_file_selection_regime
  key          text PRIMARY KEY CHECK (key IN ('convention','baranwal','act_2023'))
  position     smallint NOT NULL
  label        text NOT NULL
  from_date    date
  to_date      date
  rule         text NOT NULL
  panel        text[] NOT NULL DEFAULT '{}'
  entry_ids    text[] NOT NULL DEFAULT '{}'
  notes        text

eci_file_selection
  id             text PRIMARY KEY
  position       smallint NOT NULL          -- file order (chronological)
  date           date NOT NULL
  date_precision text NOT NULL CHECK (date_precision IN ('day','month','year'))
  date_meaning   text
  regime         text NOT NULL REFERENCES eci_file_selection_regime(key)
  method         text NOT NULL CHECK (method IN ('executive_appointment','elevation_of_senior_ec','selection_committee'))
  appointed      jsonb NOT NULL DEFAULT '[]'
  members        jsonb NOT NULL DEFAULT '[]'
  search         jsonb                      -- null when none
  dissent        jsonb NOT NULL DEFAULT '[]'
  entry_ids      text[] NOT NULL
  notes          text

eci_file_selection_person                   -- query index: "selections involving this person"
  selection_id  text NOT NULL REFERENCES eci_file_selection(id) ON DELETE CASCADE
  person_slug   text NOT NULL REFERENCES eci_file_person(slug) ON DELETE CASCADE
  part          text NOT NULL CHECK (part IN ('appointed','recommended','proposed','voted_with_majority','dissented','search_chair'))
  PRIMARY KEY (selection_id, person_slug, part)
  INDEX (person_slug)

eci_file_departure
  id           bigserial PRIMARY KEY
  date         date NOT NULL
  person_slug  text NOT NULL REFERENCES eci_file_person(slug) ON DELETE CASCADE
  office       text NOT NULL
  how          text NOT NULL CHECK (how IN ('resigned','tenure_ended'))
  notes        text
  entry_ids    text[] NOT NULL
```

- The downgrade drops the four new tables, the index and the five columns.
- `alembic check` must stay clean. These tables stay out of `MANAGED_TABLES`, as the earlier ECI tables are.
- `entry_ids` arrays cannot carry FKs, so the loader validates them (§5.2).

### 5.2 Loader changes (`pipelines/curated/eci_files.py`)

- **Two optional files**, following the `states.json`/`headline.json` pattern:
  - `DEFAULT_SELECTIONS_PATH = data/eci_files/selections.json` and `DEFAULT_MEDIA_PATH = data/eci_files/people_media.json`.
  - Both are loaded only when `run()` uses the default entries path, or when the caller passes `selections_path=`/`media_path=` explicitly.
- **Pydantic models:**
  - `SelectionRegime`, `SelectionAppointee`, `SelectionMember` (`person_slug: str | None`, `name: str | None`, `role`, `part` limited to the 5 non-appointed values, `entry_ids: list[str]` min 1), `SelectionSearch`, `SelectionDissent`, `Selection`, `Departure`, `SelectionsFile`.
  - `PersonMedia` and `MediaFile`.
  - `extra="ignore"`, and dates go through `_partial_date`.
- **Validation.** Collect every error and raise them all at once, as the loader already does:
  - every `entry_ids` / `response_entry_ids` id is a loaded (non-excluded) entry id;
  - every `person_slug`, `chair_slug` and `replaced` is a slug in the person set built from the entries;
  - every selection's `regime` is a declared regime key;
  - selection ids are unique;
  - every media `slug` is a person slug.
  - Error text names the file, the selection id and the offending value.
- **Groups.** `_role_group(details) -> (group, rank_key)` and `_is_current(tenure)` implement §1.4 exactly. After building `names_by_slug`/`profile_by_slug`, compute the group per profile and then `group_rank` as `enumerate(sorted(...))` within each group. Write `role_group, group_rank, is_current, first_from, last_to` in the existing `eci_file_person` insert.
- **Inserts.** In the same `session_scope()` full replace, delete in this order *before* the existing deletes: `eci_file_selection_person`, `eci_file_selection`, `eci_file_selection_regime`, `eci_file_departure`, `eci_file_person_media`. Insert after persons and entries exist. `eci_file_selection_person` gets one row per appointee (`appointed`), per member with a slug (their `part`) and per `search.chair_slug` (`search_chair`). Dedup with `ON CONFLICT DO NOTHING`.
- **Summary print.** Add one line: `[eci-files] loaded 3 regimes, 8 selections, 6 departures, 9 photos`.
- **Data fix.** Apply the `Justice Sanjay Kumar` change in `entries/selection-law.json` (see "What already exists").

### 5.3 Service (`api/neta_api/services/eci_files.py`)

- **`people(db)`**
  - Returns rows ordered by `CASE role_group WHEN 'commission' THEN 0 WHEN 'secretariat' THEN 1 WHEN 'state' THEN 2 ELSE 3 END, group_rank, name`.
  - Adds `group, group_rank, current, service, first_from, last_to, status_counts, photo`.
  - `status_counts` comes from one grouped query: `SELECT ep.person_slug, e.status, count(*) … WHERE e.kind <> 'person' GROUP BY 1,2`.
  - `entry_count` also excludes `kind='person'`, so it matches what the profile shows.
  - `photo` is a `LEFT JOIN eci_file_person_media`.
- **`person_page(db, slug)`**
  - `person` gains `role, tenure, service, group, current, photo, status_counts`.
  - `entries` now excludes `kind='person'`.
  - Add `selections`: every `eci_file_selection` whose id is in `eci_file_selection_person` for this slug, shaped by `_selection_payload()` and ordered by date descending.
  - Add `entries_index`: compact refs (`id, title, date, date_precision, status`) for every id cited by those selections.
- **`selections(db)`** returns `{regimes, selections, departures, entries_index}`.
  - Member payloads gain `has_profile: bool`, true when the slug has a `profile_entry_id`.
  - Appointee payloads gain `photo`, so cards can show the avatar without a second call.

### 5.4 API shapes (`schemas.py`, `routers/eci_files.py`)

```python
class EciPhoto(BaseModel):
    url: str; source_page: str; attribution: str; licence: str; licence_url: str
    licence_review: str            # reviewed | uploader_asserted
    original_publisher: str | None = None; caption: str | None = None; photo_date: date | None = None

class EciStatusCounts(BaseModel):
    documented: int = 0; reported: int = 0; claim: int = 0; response: int = 0

class EciEntryRef(BaseModel):                      # for labelling cited ids
    id: str; title: str; date: _Date | None = None; date_precision: str; status: str

class EciPersonSummary(BaseModel):                 # GET /eci-files/people (still a list)
    slug: str; name: str
    group: str                                     # commission | secretariat | state | named
    group_rank: int
    current: bool
    role: str | None = None
    service: str | None = None
    tenure: list[Any] = Field(default_factory=list)
    first_from: date | None = None; last_to: date | None = None
    entry_count: int
    status_counts: EciStatusCounts
    photo: EciPhoto | None = None

class EciSelectionAppointee(BaseModel):
    person_slug: str; name: str; office: str; took_charge: date | None = None
    replaced: str | None = None; photo: EciPhoto | None = None
class EciSelectionMember(BaseModel):
    person_slug: str | None = None; name: str | None = None; role: str; part: str
    has_profile: bool = False; entry_ids: list[str]
class EciSelectionSearch(BaseModel):
    by: str; chair_slug: str | None = None; shortlist_size: int | None = None
    shortlist: list[str] | None = None; shortlist_source: str | None = None; entry_ids: list[str]
class EciSelectionDissent(BaseModel):
    person_slug: str; name: str; summary: str; note_public: bool; status: str
    entry_ids: list[str]; response_entry_ids: list[str] = []
class EciSelection(BaseModel):
    id: str; date: _Date; date_precision: str; date_meaning: str | None = None
    regime: str; method: str
    appointed: list[EciSelectionAppointee]; members: list[EciSelectionMember]
    search: EciSelectionSearch | None = None; dissent: list[EciSelectionDissent]
    entry_ids: list[str]; notes: str | None = None
class EciSelectionRegime(BaseModel):
    key: str; label: str; from_date: date | None = None; to_date: date | None = None
    rule: str; panel: list[str]; entry_ids: list[str]; notes: str | None = None
    selection_count: int
class EciDeparture(BaseModel):
    date: _Date; person_slug: str; name: str; office: str; how: str
    notes: str | None = None; entry_ids: list[str]
class EciSelections(BaseModel):                    # GET /eci-files/selections
    regimes: list[EciSelectionRegime]; selections: list[EciSelection]
    departures: list[EciDeparture]; entries_index: list[EciEntryRef]

class EciPersonDetail(BaseModel):
    slug: str; name: str; profile: EciEntry | None = None
    group: str; current: bool; role: str | None = None; service: str | None = None
    tenure: list[Any] = Field(default_factory=list)
    status_counts: EciStatusCounts; photo: EciPhoto | None = None
class EciPersonPage(BaseModel):
    person: EciPersonDetail
    entries: list[EciEntry]                        # kind='person' excluded
    selections: list[EciSelection]                 # as appointee, member or search chair
    entries_index: list[EciEntryRef]
```

- **Router.** Add `GET /eci-files/selections` → `EciSelections`, with the same cache headers as the other read routes.
- **OpenAPI.** Regenerate `docs/eci-files/openapi.json`.
- **Compatibility.** Existing fields keep their names, so the current web keeps working until the web worker switches over.

### 5.5 Registry, docs

- `ingestion/source_registry/eci_files_curated.yaml`: extend `conversion.produces` with `eci_file_selection` and `eci_file_person_media`. Update `ingestion/tests/test_pipeline_contracts.py` if it asserts `produces`.
- `docs/OPERATIONS.md`, ECI Files section:
  - one paragraph on `selections.json` and `people_media.json`;
  - the photo script (`uv run --with pillow python scripts/eci_files_fetch_photos.py`);
  - the rule that a new photo needs a GODL/CC licence on its file page and an attribution line.
- `docs/data-sources.md`: one row, "ECI Files photos: Wikimedia Commons, GODL-India, attribution per file".
- These docs go in the same commit as the code.

### 5.6 Backend tests (`ingestion/tests/test_eci_files.py` + fixtures)

Add fixtures `ingestion/tests/fixtures/eci_files/extra/selections.json` and `people_media.json`, small and referencing the fixture entries. Tests:

1. **Grouping.** One test per rule in §1.4, including precedence: a profile with both an EC and a CEO tenure is `commission`. Rank order is chronological. `is_current` is false when `from` is null.
2. **Selections validation.** Each of these raises `EciFilesValidationError` and names the value: an unknown entry id, an unknown slug, an unknown regime, a duplicate selection id, and a member with an empty `entry_ids`.
3. **Media validation.** An unknown slug is rejected, and a bad `licence_review` is rejected.
4. **Postgres** (skipped without `NETA_TEST_DATABASE_URL`):
   - Loading twice gives identical counts in all five new tables.
   - `eci_file_selection_person` contains `appointed`, `dissented` and `search_chair` rows for the fixture.
   - The `url` column holds `local_path` when `self_host` is set.
5. **Real data smoke test** (skipped unless `NETA_ECI_REAL_DATA=1`). `run()` validates the repo's real `selections.json`/`people_media.json` without a DB, by calling the validation functions only.

---

## 6. Work split

### BACKEND worker owns

| Path | Change |
| --- | --- |
| `data/eci_files/entries/selection-law.json` | the one-name fix (Justice Sanjay Kumar) |
| `backend/database/migrations/versions/0008_eci_files_people.py` | §5.1 |
| `ingestion/neta_ingest/pipelines/curated/eci_files.py` | §5.2 |
| `ingestion/tests/test_eci_files.py`, `ingestion/tests/fixtures/eci_files/extra/*` | §5.6 |
| `ingestion/source_registry/eci_files_curated.yaml`, `ingestion/tests/test_pipeline_contracts.py` | §5.5 |
| `api/neta_api/services/eci_files.py`, `api/neta_api/routers/eci_files.py` | §5.3–5.4 |
| **`api/neta_api/schemas.py`** (hotspot, backend only) | §5.4 |
| `docs/eci-files/openapi.json` | regenerate |
| `scripts/eci_files_fetch_photos.py` **and its output `web/public/eci-files/people/*.jpg`** | §4.2. The web worker never writes these files. |
| `docs/OPERATIONS.md`, `docs/data-sources.md` | §5.5 |

Backend does not edit `data/eci_files/selections.json` or `people_media.json`. If validation fails on them, report it; don't change the facts.

### WEB worker owns

| Path | Change |
| --- | --- |
| `web/src/app/eci-files/people/page.tsx` | rewrite (§1) |
| `web/src/app/eci-files/people/[slug]/page.tsx` | rewrite (§2) |
| `web/src/app/eci-files/selections/page.tsx` | new (§3) |
| `web/src/components/eci-files/` new: `PersonAvatar.tsx`, `TenureBar.tsx`, `CommissionTenureChart.tsx`, `StatusCountBar.tsx`, `StateOfficerTable.tsx`, `NamedPeopleList.tsx`, `ProfileHeader.tsx`, `KeyFacts.tsx`, `CareerTimeline.tsx`, `SelectedByBlock.tsx`, `PanelSeatsBlock.tsx`, `SelectionCard.tsx`, `SelectionGraph.tsx`, `RegimeCompare.tsx`, `PersonEntrySections.tsx`, `PhotoCredits.tsx`, `SectionNav.tsx` | §1–4 |
| `web/src/components/eci-files/PersonCard.tsx` | rewrite |
| `web/src/components/eci-files/LaneTimeline.tsx` | add `hideEmptyLanes` (default false) |
| `web/src/components/eci-files/EntryDetail.tsx` | optional `basePath` prop |
| **`web/src/lib/eci-files.ts`** (hotspot, web only) | `ECI_TENURE_AXIS`, `tenureSegments`, `membersInOffice`, `careerTimeline`, `sourceKind`, `initials`, `personGroupMeta`, `photoCredit`, `eciEntryHref(…, basePath)`. Delete `detailLines` if unused. |
| **`web/src/types/eci-files.ts`** (hotspot, web only) | hand-write the §5.4 shapes now; switch to generated types after codegen |
| **`web/src/lib/api.ts`** (hotspot, web only) | `getEciSelections()` (revalidate 3600), re-export the new types |
| `web/src/types/api.ts` | `npm run codegen` once the backend is merged and running |
| **`web/src/app/globals.css`** (hotspot, web only) | classes below, no new hex |

**`globals.css` additions.** Put them under the existing ECI block. They are role-based and use tokens and `color-mix` only:

- `.eci-avatar`, `.eci-avatar-initials` (bg `color-mix(in srgb, var(--eci-ink) 13%, var(--card2))`, text `var(--eci-ink)`, weight 600)
- `.eci-section-nav`
- `.eci-tenure-bar`, `.eci-tenure-ec`, `.eci-tenure-cec`, `.eci-tenure-other`
- `.eci-career` (rail), `.eci-career-item`, `.eci-career-item[data-commission]`
- `.eci-keyfacts` (4-col grid, 2×2 under 640px)
- `.eci-profile-grid` (1fr 300px at ≥960px)
- `.eci-graph`, with `.eci-graph[data-focus] .eci-edge:not([data-on]) { opacity: .25 }`
- `@media (max-width: 719px) { .eci-graph { display: none } }`

**`PersonAvatar({ name, photo, size, decorative })`**

- **With a photo.** Render `<img src={photo.url} width height loading="lazy" decoding="async" class="eci-avatar">`, a circle with a 1px `--rule` ring.
  - `alt=""` when `decorative`, i.e. the name is printed beside it, as in cards.
  - Otherwise `alt="Photo of {name}"`.
- **Without a photo.** Initials in a circle, `aria-hidden`.
  - `initials(name)`: split on whitespace, strip `.`, ignore tokens of length 1 unless they are the only token, then take the first char of the first and last remaining tokens, uppercased.
  - A leading `Justice` is dropped first.
  - Examples: `A. Sreenivas` → `AS`, `Rathan U. Kelkar` → `RK`, `Justice Sanjay Kumar` → `SK`.

**Order and coordination.**

- The backend lands the migration, loader and API first. The web worker codes against §5.4 in parallel, and every page must render its failure copy when the API is down (the existing `The record hasn't loaded — try again in a moment.`).
- The build must not need the API.
- Neither worker edits the other's hotspots. If one needs a change there, they write it in their PR notes for the other.

---

## 7. Accessibility, mobile, acceptance

### Accessibility

- **Headings.** Each page has one `h1`. Group and section headings are `h2`, and cards use `h3` (the name) inside a link.
- **Colour is never the only carrier.**
  - EC vs CEC bars: the legend and aria-labels say the office.
  - Dissent: dashed line, an `×` and the text `Dissented`.
  - Status bars: always paired with the count text.
  - Serving: a text chip.
- **Charts.**
  - The tenure chart has `<figure>`/`<figcaption>`, per-row link aria-labels and a table alternative.
  - The selection graph is `role="img"`, with the full selection list as the accessible form.
  - Tenure bars are `role="img"` with text labels.
- **Keyboard.**
  - Every row, node, diamond and card is a native link or button with a visible `:focus-visible` outline (`2px solid var(--eci-ink)`).
  - The drawer keeps its Esc and focus behaviour.
  - "Show all" buttons have `aria-expanded`.
- **Images.** `alt` follows the rule above. Photos never carry text.
- **Contrast.** Initials text (`--eci-ink` on its 13% tint) must reach 4.5:1 in both themes. Verify both, and darken the tint (not the text) if needed.
- **Motion.** Hover dimming in the graph is disabled under `prefers-reduced-motion`.

### Mobile (400px must work, no horizontal scroll)

- **People page.**
  - Cards are one column.
  - The tenure chart stacks the name above each bar, uses 2-digit year ticks, and keeps the markers with their labels shortened (`Court rule`, `2023 Act`).
  - The state table becomes two-line rows.
  - The named list has 2 columns.
- **Profile.**
  - The avatar is 72px.
  - Key facts are 2×2.
  - The career date sits above the post.
  - The right rail stacks after Career.
  - `LaneTimeline` uses its existing phone card stream.
- **Selections page.** The graph is hidden. The regime cards stack. The selection cards are full width.

### Acceptance checks (a reviewer runs these)

**Data and backend**

1. `uv run neta eci-files` prints the new summary line: `3 regimes, 8 selections, 6 departures, 9 photos`.
2. `uv run pytest ingestion/tests/test_eci_files.py` passes. `ruff check` is clean in ingestion and api. `alembic upgrade head`, `downgrade -1`, `upgrade head` and `alembic check` are all clean.
3. `curl -s localhost:8000/eci-files/people | jq '[.[] | select(.group=="commission") | .slug]'` returns exactly `["sunil-arora","ashok-lavasa","sushil-chandra","rajiv-kumar","anup-chandra-pandey","arun-goel","gyanesh-kumar","sukhbir-singh-sandhu","vivek-joshi"]`.
4. On `/eci-files/people/gyanesh-kumar`:
   - `.selections | length == 2`;
   - the 2025 one has `dissent[0].person_slug == "rahul-gandhi"`, and the 2024 one has `"adhir-ranjan-chowdhury"`;
   - `.person.photo.url == "/eci-files/people/gyanesh-kumar.jpg"`.
5. `/eci-files/selections`:
   - `.selections | length == 8`;
   - `.regimes[] | select(.key=="baranwal") | .selection_count == 0`;
   - every id in any `entry_ids` appears in `.entries_index`.
6. `/eci-files/people/sanjay-kumar` does not include `selection-law-cji-khanna-recuses`, and `/eci-files/people/justice-sanjay-kumar` does.
7. No `entries` array on any person page contains a `kind == "person"` entry.
8. `ls web/public/eci-files/people/` lists exactly the 9 slugs as `.jpg`. Each is at most 480px square and under 90 KB.

**Web**

9. `npm run lint`, `npm run typecheck` and `npm run build` pass, and the build runs with the API down.
10. The page source of `/eci-files/people`, one profile and `/eci-files/selections` has `<meta name="robots" content="noindex, nofollow">`. None of the three is in `sitemap.ts` or linked from `SiteHeader` or the homepage.
11. The string `born`, and any date of birth, appears on no profile. Check `sunil-arora`, `gyanesh-kumar` and `vivek-joshi`.
12. `/eci-files/people/pramod-kumar-sharma` renders with initials, `Tenure dates not on record`, and no empty section or nav chip.
13. `/eci-files/people/rahul-gandhi` shows `Named in the record`, a `Sat on selection panels` line for 17 Feb 2025 with `Dissented`, and no KeyFacts.
14. On the Gyanesh Kumar profile the career list shows two undated postings under `Postings listed without dates`, and the Kerala Secretary line reads `until 2006`. `Resident Commissioner, Kerala House` reads `from 2012 · end date not in source`, not "present".
15. Clicking a lane dot, a section card or a `Cited:` link on a profile opens the drawer on the same profile URL (`?entry=`). Esc closes it and returns focus to the page.
16. At 400px wide there is no horizontal scroll on any of the three pages, and the selection graph is not rendered.
17. With the keyboard alone, Tab reaches every tenure-chart row and diamond, the selection graph nodes and every card, each with a visible focus ring.
18. Each profile photo has a visible credit linking to its Commons page, and the people page's "Photo credits" lists all 9.
19. No new hex colour appears in the diff outside `globals.css`, and none inside it either. Only tokens and `color-mix` are used.

---

## Open questions for the owner

1. **Four photos are only uploader-tagged as open-licence (Arora, Chandra, Pandey, Joshi).** The Commons uploaders tagged eci.gov.in images as GODL-India, but no reviewer confirmed it, and eci.gov.in itself says "© Election Commission of India".
   - (a) Use them now with attribution, as in `people_media.json`.
   - (b) Show initials for these four until ECI grants permission.
   - (c) Use them now and email ECI's web team for written permission in parallel. Swap to initials if they refuse.
   - *Recommendation: (c).* The licence tag is plausible, the risk is low, and a row of nine commissioners where four are initials would read as a judgment about those four.
2. **Where the selection network lives.**
   - (a) Its own page `/eci-files/selections`, linked from the people page and profiles.
   - (b) A section at the bottom of `/eci-files/people`.
   - (c) Both: a compact regime-compare strip on the people page, and the full graph on its own page.
   - *Recommendation: (a).* It keeps the people page about people and gives the network room to breathe. (c) adds a second place to keep in sync.
3. **Profile pages for people named only in passing (56 judges, lawyers, ministers and party leaders).**
   - (a) Keep a page each, listing the entries that name them (as specified).
   - (b) No page: link their names to `/eci-files/timeline?person=` instead.
   - (c) Keep pages and add a one-line role for each from a small curated file.
   - *Recommendation: (a) now, (c) later.* Pages cost nothing and the panel members need somewhere to land. A curated role file is new research and belongs in its own pass.
4. **Naming judges so they don't collide with officials.** This phase renames one judge to "Justice Sanjay Kumar" to fix a slug collision.
   - (a) Only this one.
   - (b) Prefix every sitting or former judge in the entries with "Justice" for consistency.
   - (c) Add an alias map (`name → slug`) to the loader and leave the data alone.
   - *Recommendation: (b), in phase 5's data pass.* It makes the named list readable (you can see who is a judge) and prevents the next collision. It is a data edit across files, so it shouldn't ride on this phase.
5. **Showing the 14 objections on Sandhu's and Joshi's profiles.** `objections.json` is scheduled for phase 5.
   - (a) Wait for phase 5. The objection entries already appear under "Decisions & objections" through the Inside lane.
   - (b) Load `objections.json` now and add a "Recorded objections: n of 14" tile to those two profiles.
   - *Recommendation: (a).* It keeps this phase's scope, and phase 5 is where the objections get their own treatment.
