# Owner decisions for phases 3-5 (26 Sep 2026)

These override the defaults in PHASE3/4/5-SPEC.md where they differ.

## Asked and answered

- **Photos.** Use only the five reviewer-confirmed Commons photos (Gyanesh Kumar, Sukhbir Singh Sandhu, Rajiv Kumar, Arun Goel, Ashok Lavasa). Arora, Chandra, Pandey and Joshi show initials until their licence is confirmed. `people_media.json` already reflects this; see `held_pending_licence_confirmation`. The UI must look deliberate either way: initials use the same size and frame as photos.
- **Form 6 diff.** Publish it with per-line labels ("quoted in reporting", "paraphrased from reporting"). Never show it as verbatim. Keep the third status, "quoted in reporting".
- **Phase III states with only press tallies.** Show "no figures yet" with the tally in that state's notes. A separate researcher is looking for official counts; don't wait for it.
- **Empty objection slots.** The label is exactly: "Not itemised in the published reports".

## Taken as recommended by the spec writers

- **Appeals.** Shown on state pages only, not as a tile measure. Only West Bengal has a figure.
- **Goa's `restored: 97`.** Moves into Goa's notes.
- **Phone layout.** Under 480px, /numbers opens on the table view.
- **The selection network.** Gets its own page, /eci-files/selections.
- **People named only in passing.** Keep a simple page listing the entries that name them.
- **Judges.** Prefix every judge's name with "Justice", so a judge can never share a slug with an official. This is part of the phase 5 data pass.
- **Objections on profiles.** Wait for phase 5. The objection entries already show under "Decisions & objections".
- **Rows where the Commission acted first.** They stay on /answers under the neutral heading "What was said or done".
- **The seven duplicate charge groups.** Ship them marked in `pairs.json`, and merge them in the next data pass.
- **The 2023 Act text taken from the bill.** Keep it labelled verbatim, and add a pre-launch check to confirm it.
- **"What the record shows".** Documented entries only.
