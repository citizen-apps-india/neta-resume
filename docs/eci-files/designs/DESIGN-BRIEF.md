# ECI Files: review and rework brief (for designers)

ECI Files is a hidden section of neta-resume: a sourced public record of the Election Commission of India. The
owner's verdict on the built pages: random UI, no visual hierarchy, no clean visual understanding, and far too much
text. **People don't want to read. Show, don't tell.**

The timeline has already been reworked in this canvas. Read `project/Main.dc.html` (desktop) and
`project/Mobile.dc.html` (phone) as the reference for components and tone, and `gen.py` for how they were generated.
Your pages must look like the same product.

## Principles (non-negotiable)

1. **One visual answer per page, above the fold.** Every page opens with the single chart, diagram or big number
   that answers the page's question. Text supports it; it never replaces it.
2. **Text budget.**
   - Page title: 8 words or fewer.
   - At most one supporting line under it, 15 words or fewer.
   - No paragraphs on first view. Long text (summaries, notes, methods) goes behind a "Details" or "Read more"
     control, drawn collapsed.
   - Labels beat sentences; numbers beat words.
3. **Hierarchy.** Exactly one hero element, then scannable rows or cards of equal weight, then the detail.
   Everything is aligned to one grid. Whitespace separates groups; borders are rare.
4. **Colour means one thing.** The lane colours (below) identify the kind of event. Status is a word:
   Document, Reported, Claim or Response. Checked is a small tick plus the word; unchecked is "Not yet checked".
   Charts use one hue where they can.
5. **Sourced-record stance stays.** Every claim is attributed. A charge always shows its answer, or
   "No response on record". There are no verdict words in our voice. A source is one tap away, but needn't be
   printed in full.
6. **Real data only.** Take every name, number, date and title from the live API (below). No invented stats and no
   lorem ipsum. If a number isn't available, use a labelled placeholder like `[count]`.

## Design language

- **Fonts.** "Bricolage Grotesque" for display and body (weights 400–700), and "IBM Plex Mono" for dates, counts and
  small labels. Load both with this Google Fonts `<link>` inside `<helmet>`:
  `https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,400;12..96,500;12..96,600;12..96,700&amp;family=IBM+Plex+Mono:wght@400;500&amp;display=swap`
- **Neutrals.**

  | Role | Value |
  | --- | --- |
  | Ground | `#F5F6F7` |
  | Card | `#FFFFFF` |
  | Rule | `#E2E4E8` |
  | Border | `#DADDE2` |
  | Ink | `#121317` |
  | Ink 2 | `#4B4F59` |
  | Muted | `#80858F` |
  | Faint | `#A0A4AD` |

- **Section accent.** `#6D3FA0`, ECI violet, used sparingly: links, the active state, key moments.
- **Lanes.**

  | Lane | Colour |
  | --- | --- |
  | Commission | `#2a78d6` |
  | Inside the Commission | `#6D3FA0` |
  | Courts | `#4B4F59` |
  | Claims | `#d4541f` |
  | Responses | `#128a60` |

- **Sequential ramp** for maps and tiles (light to dark violet): `#EEE6F7 #D4C2EA #B195D8 #8B63C2 #6D3FA0 #4A2474`.
- **Checked tick.** `#1C7A4C`.
- **Shape.** Cards have a 14px radius, a 1px `#E2E4E8` border and no heavy shadows. Pills have a 999px radius.
  Touch targets are at least 40–44px.
- **Artboards.** Desktop is 1440 wide, with height as the content needs (keep it under 2400). Phone is 390×844.
  Page padding is 64px on desktop and 16px on phone.

## File format (Claude Design `.dc.html`): rules that fail silently if broken

- Each artboard is ONE self-contained file in the skeleton `gen.py` uses: `<!doctype html>`, then `<head>` with
  `<meta charset>`, `<title>` and EXACTLY `<script src="./support.js"></script>`; then `<body><x-dc><helmet>` (the
  font `<link>` and a `<style>` with `body{margin:0;...}` only)`</helmet>` followed by your root `<div>`, and
  `</x-dc>`.
- End with `<script type="text/x-dc" data-dc-script data-props='{"$preview":{"width":W,"height":H}}'>` containing
  `class Component extends DCLogic { renderVals() { return {}; } }` and `</script></body></html>`.
- The root `<div>` has a FIXED `width`/`height` equal to the board size. Styles go inline in `style="..."`; lay out
  with flex or grid plus `gap`.
- Close every element and quote every attribute.
- Images: only the uploaded before images, by their `/_blob/...` url, verbatim. No other images, no emoji, no
  iframes. Icons are inline stroke SVG.
- Use real `<button>`, `<a href>`, `<input>`, `<select>` and `<label>` elements, and an `aria-label` on icon-only
  buttons. Text contrast is at least 4.5:1.
- No `{{holes}}` needed: write static markup. You may generate the files with a Python script, as `gen.py` does.

## Before boards (the review)

For each page, make `<Group>-Before-<Page>.dc.html` at 1440×760, following the pattern of `project/Before.dc.html`:
- **Left.** The before image at 960px wide, keeping its aspect ratio (the source images are about 913–941px wide),
  with 4–6 numbered orange pins (`#d4541f`, with a white ring) placed over the problems.
- **Right.** A numbered list of the same issues. Each is a bold title of 6 words or fewer plus ONE line of 14 words
  or fewer. Terse.

Before image urls:

| Page | Before image |
| --- | --- |
| front-top | /_blob/584df0841390fe0d528ae95dc89bdcdb |
| front-lower | /_blob/8caff129f6a13fb8841b6ebfd0a68c91 |
| numbers-top | /_blob/7664e8e4d78b2190c7b02801dba1aaae |
| numbers-tiles | /_blob/75e6fa6d9c857e9eaf076ffc6adf2cc4 |
| state | /_blob/11d97cdd6e2bcfe83a9c50d65658f8ca |
| people | /_blob/5e8a426d8e12e8457bf1e196639d8d5d |
| profile-top | /_blob/9829b60b60f3f7f3c640a8770c929c0f |
| profile-career | /_blob/6da9a091be484fbf58eda7733a520591 |
| selections | /_blob/5725f10357773eb0773b4c64ee445d8e |
| objections-top | /_blob/dfe4f5a8a7d4e5e929d884d8f65a8480 |
| objections-ledger | /_blob/62177132cdd4457eac04d18069b03ebb |
| answers | /_blob/d6f0a7501d88f7a9dc633eeacefb8f82 |
| rules-list | /_blob/61231497ba11ace932437fc1bd40bf50 |
| rule-diff | /_blob/148d7cb184e0a6cb8707e403c9f0f8e2 |
| courts-list | /_blob/39d4a429bf6210f752fc6acd3efec25d |
| court-case | /_blob/6fcc99c30b0f487c9d0b9fc432f7af45 |
| entries | /_blob/35501d952048a350dd9872b0412882e2 |

The same images are on disk at `before/<name>.jpg`; open them with your image-reading tool to see what you're
reviewing.

## After boards (the rework)

For each page, make `<Group>-After-<Page>.dc.html` (desktop), plus `<Group>-Phone-<Page>.dc.html` for your group's
main page. Show one realistic state, and where a state matters show it too: one item expanded, or a filter
applied.

## Real data

The API is live at `http://localhost:8765` (use curl). Useful routes:

| Route | What it returns |
| --- | --- |
| `/eci-files/summary` | Headline stats and key moments |
| `/eci-files/timeline?fields=compact&from=&to=` | Timeline entries |
| `/eci-files/entries/{id}` | One entry |
| `/eci-files/states` | All states |
| `/eci-files/states/{slug}` | One state |
| `/eci-files/people` | People |
| `/eci-files/people/{slug}` | One person |
| `/eci-files/selections` | Selections |
| `/eci-files/objections` | Objections |
| `/eci-files/answers` | Charge-and-answer pairs |
| `/eci-files/rules` | Rules |
| `/eci-files/rules/{diff-id}` | One rule diff |
| `/eci-files/courts` | Court cases |
| `/eci-files/courts/{slug}` | One court case |

The live site (for reference only) is at `http://localhost:3765/eci-files/...`.

Photos: only these five have a licensed photo — Gyanesh Kumar, Sukhbir Singh Sandhu, Rajiv Kumar, Arun Goel and
Ashok Lavasa. In mockups, draw EVERY person as initials in a circle (same size and frame), and add a small note
saying the photo slot uses the licensed photo where one exists. Never show personal details such as dates of
birth.

## Output

- **Where.** Write your files into `project/` in this folder:
  `/private/tmp/claude-501/-Users-sahilsawant-repos-djinn-amartya-djinn/77bccf03-0470-430d-a1b3-f78ac5b29501/scratchpad/tl-design/project/`.
  Use unique names with your group prefix. Never touch `Main.dc.html`, `Mobile.dc.html`, `Before.dc.html` or
  `canvas.json`.
- **Manifest.** Write `manifests/<Group>.json`:
  `{"page": "<Section name>", "boards": [{"file": "<name>.dc.html", "w": 1440, "h": <h>, "title": "<short title>", "row": 0|1, "col": 0..n}]}`.
  Row 0 holds the before boards and row 1 the after boards; phone boards go in row 1 after the desktop boards.
- **Don't publish, and don't render or screenshot to check.** Write carefully and validate that each file is
  well-formed; a Python HTML parser check is fine.
- **Return** a short summary: the boards you made, the 3–5 core design moves per page, and any data you couldn't
  get.
