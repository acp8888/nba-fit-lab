# Series revision — reframing "Fit, Quantified"

Working doc for reshaping the blog series. The **analysis is sound; the framing was
broken** (Post 1 asserted a fit-problem thesis that Posts 2–3 refute). This installs an
honest through-line, specs the new analyses, and lists the data still needed.

## The corrected through-line

We set out to *price fit* and found it's **mostly talent** — with one exception (rim
protection) and one real mechanism (talent **saturates**). Post 1 must set up a genuine
open question the later posts answer, consistent with what they find:

> **When your best player is a ball-dominant non-shooter, what do you build around him —
> and does anything actually work?**

Both teams are built around the same star archetype (Banchero, Williamson). Orlando
**duplicated** it (Franz Wagner: another high-usage non-shooting creator); New Orleans
**complemented** it (Trey Murphy: elite spacer). **Both bets underachieved** — which is
live evidence for Post 2's thesis: if the "add spacing" solution *also* failed, spacing
was never the answer. The Mosley move (ORL→NOP: he coached the duplicate build, now
inherits the complement build) is the third leg → Post 5.

Personal hook to keep in prose: *I like both teams, both have failed to reach their
potential around their stars, and a coach is moving between them.*

---

## The verified empirical spine (do not assert — this is measured)

League percentiles, rotation players (MP≥800), from `stg_player_advanced` (usage, 3PA
rate, assist%, TS%) + NBA.com shot types (catch-&-shoot gravity). Both seasons.

| player | team | usage | 3PA rate | C&S gravity | assist | read |
|---|---|---|---|---|---|---|
| **Banchero** | ORL | 91–98th | 18–22nd | 17–19th | 81–86th | ball-dominant non-shooter |
| **Wagner** | ORL | 89–97th | 21–23rd | 28–29th | 66–88th | **≈ Banchero → duplicate** |
| **Williamson** | NOP | 85–99th | 4–7th | 0–10th | 64–97th | ball-dominant non-shooter |
| **Murphy** | NOP | 71–74th | 70–74th | **81st** | 58–60th | **elite spacer → complement** |
| Carter / Bitadze | ORL | low | 8–34th | 8–31st | — | non-shooting bigs |
| Missi | NOP | low | 2–3rd | 0 | — | non-shooting big |
| **Queen** (25-26 only) | NOP | **66th** | 11th | 11th | 76th | **high-usage non-shooter → 2nd duplicate** |

**Finding (honest, not tidy):** the duplicate-vs-complement inversion is **clean and
strong at the wing** (Wagner duplicates Banchero; Murphy complements Zion) but **breaks at
center** — both teams stack non-shooting bigs, and New Orleans's Queen is itself a
high-usage non-shooter. So NOP only *half*-complemented: elite spacing at the 2, another
ball-dominant non-shooter at the 5. A one-position inversion is still a finding, and this
messier version is the *stronger* story (NOP had the elite spacer and still went 26-56 →
spacing wasn't the answer).

---

## Audit findings (rules 1 & 6)

- **Framing contradiction confirmed & fixed** by the reframe above. Post 2's findings are
  untouched.
- **Attribution/season hygiene — clean, with flags.** The notebook prose names *no*
  players (Post 1 is a style table; Post 3 uses opponent abbreviations), so nothing is
  misattributed there. **Vučević is correctly on BOS in 2025-26, not ORL** — a Post-4-only
  (2026-27) player. **Queen correctly appears in 2025-26 only.** `mart_player_proj` rosters
  are legit 2025-26.
- **Two season-boundary traps to fix in the prose:**
  1. `mart_pair_synergy` is **2024-25** while the lineup marts are **2025-26**. Any
     pairwise/WOWY claim (Banchero+Wagner, Zion+Murphy) is a **2024-25** claim; label it.
  2. **Desmond Bane** is a *shooter* who joined ORL for **2025-26** (in `mart_roster` /
     `mart_player_proj`, not the 2024-25 core). "Orlando duplicated" is about the
     **Banchero+Wagner** core; Bane was the *one* spacing patch that didn't fix it — the
     honest way to fold in the "never Bane" angle.

---

## Revised post specs

### Post 1 — "When your best player can't shoot, what do you build around him?"
- **Q:** Same star archetype, opposite bets (ORL duplicated, NOP complemented) — did either work?
- **Data:** `mart_player_proj` (ORL/NOP, 2025-26) for rim freq/PSA on named players; leaguewide percentiles from `stg_player_advanced` + NBA shot types, **both seasons** (Analyses A/B).
- **Method:** percentile fingerprints — Banchero vs Williamson (star match), then Wagner vs Murphy and the bigs (inversion). One chart: ORL's cast clustered near its star, NOP's split.
- **Takeaway:** inversion holds at the wing, breaks at center; both bets underachieved → sets up Post 2.
- **Gaps:** no leaguewide rim frequency (leans on ORL/NOP CTG for "lives at rim"); n=2 (Analysis C generalizes).

### Post 2 — "Fit, quantified" *(keep findings; retune intro)*
- **Q:** Which fit ingredient pays, and can you stack talent?
- **Data:** `mart_lineup_features_league` (2025-26) + `load_5man_features_2024()`; `mart_pair_synergy` (**label 2024-25**).
- **Method:** unchanged — regression, saturation curve, held-out replication, pair-WOWY.
- **Takeaway:** talent dominates & saturates; rim protection is the one lever; **spacing is a null — NOP's elite spacer (Murphy) is the live proof** (tie to Post 1). **Capstone (from Analysis D):** even the *threshold* version of fit is engineered away — **99% of leaguewide lineups have a creator, 98% have a spacer**, so the "no-spacing" disaster barely exists; coaches pre-empt the cliffs. Reframes ORL/NOP's problem as a *ceiling*, not a broken lineup.
- **Gaps:** keep current; **add** pairs=2024-25 vs lineups=2025-26 note; role flags are tunable heuristics.

### Post 3 — "Know your enemy" (opponent style + swing games) — REORDER REVERTED
- **Q:** Do matchups / opponent style decide games — and do close games trace to fit?
- **Data:** `mart_games_styled`, `load_games_rim`, `mart_team_style`.
- **Method:** archetype clustering (fuzzy), process-vs-outcome regression, swing games + per-game rim resolution.
- **Takeaway:** style = process not outcome; swing games mostly variance; the one real fit lever (rim protection) doesn't decide individual games either.
- **Gaps:** 171 games, one season; per-game fit too small vs. single-game noise.
- **Why reverted:** Analysis D (role coverage) came back a **NULL** (below) — a third consecutive fit-null made a poor standalone Post 3. D's punchline is folded into Post 2 as a capstone; the already-built matchups piece stays as Post 3 for variety.

### Post 4 — "The moves that matter"
- **Q:** win projections + best fit-adjusted move.
- **Data:** `mart_roster` (**2025-26 teams** — forward-looking 2026-27 needs updated rosters/DARKO; gap below).
- **Method:** DPM→pythagorean→simulation + marginal-value ranking.
- **Takeaway:** talent upgrade beats fit tweak; test "2nd shooter moves ORL most", "trading Murphy costs NOP more than his DPM."
- **Gaps:** projection uses last season's rosters.

### Post 5 — "Same coach, new roster" *(Mosley test, named predictions)*
- **Q:** Mosley coached the duplicate build, inherits the complement build — does his style travel?
- **Data:** 2-season `mart_team_style` (Analysis E, gap) + in-season refresh.
- **Method:** establish ORL's Mosley fingerprint across seasons; name coaching-vs-personnel dimensions (Analysis F) with falsifiable thresholds now.
- **Gaps:** no historical team-style or in-season data yet.

---

## New analyses ranked by value-per-effort

1. **A + B (Post 1)** — highest value, lowest effort (verified). **Do now, no pull.**
2. **C (generalize beyond n=2) — DONE (2025-26), in Post 1.** 11 teams built around a ball-dominant non-shooter; complement builds over-perform talent (**+1.8 vs +0.6** net/100; shooters-vs-fit **r=+0.69**, → +0.53 without OKC; regression +1.3/spacer, p≈0.07). Framed (per decision) as a **small edge dwarfed by talent** — *consistent with Post 2, not a contradiction* (Post 2 = lineup-level spacing null; C = smaller roster-level echo, n=11, likely partly DPM-under-pricing-shooting). **The 2024-25 team pull doubles n (→~22) and would settle it.** Also emits the `mart_player_league` archetype flags **D reuses**.
3. **D (role coverage) — DONE: NULL.** 99% / 98% of leaguewide lineups already have a creator / spacer (coaches engineer away the cliffs); no threshold effect beyond talent, and the `is_rim_protector` proxy is null too (A2's continuous rim measure already found the one real lever). Folded into **Post 2** as the "why fit stays small" capstone — not a standalone post.
4. **E (two-season style)** — Post 5 / Mosley; needs the historical pull. **Do for Post 5.**
5. **F (Mosley portability)** — spec now (dimensions from `mart_team_style`), grade in-season; depends on E.

---

## Data-export list (prioritized) & what it unlocks

1. **Nothing** for Posts 1–2 core — build `mart_player_league` (leaguewide percentiles + archetype flags) **from existing staging** (BBref advanced + NBA shot types + DARKO, both seasons). *Highest leverage, no pull.*
2. **BBref *and* CTG 2024-25 (+ Mosley tenure) leaguewide team stats** → **two** historical `mart_team_style` variants: **public** (BBref — powers the companion) + **private** (CTG-rich: transition/half-court PPP, garbage-time filtering, zone rates — for analysis/charts, credited). CTG-derived marts stay under a private prefix per the guardrail. → Analysis E / Post 5.
3. **PBPStats leaguewide per-player shot distribution, both seasons** (public) → sharpens "lives at rim" + leaguewide shot flags (A/C/D). *Offense only — not rim protection.*
4. **Current DARKO (2026-27)** → Post 4 forward-looking.
5. **(Optional, heavy) leaguewide 2025-26 2-man + on/off** → pair-season parity. We already have ORL/NOP 2025-26 pairs; leaguewide is optional.

---

## Decisions (resolved)

1. **Pull BOTH CTG and public** for historical team style. Public (BBref) powers the interactive companion; the CTG-rich variant stays under a **private** prefix for analysis/charts (aggregates credited "via Cleaning the Glass"). This keeps the licensing guardrail structural.
2. **Post 3 = opponent/matchups** (reorder reverted — Analysis D came back null). D's range-restriction punchline folds into Post 2 as a capstone.

---

## Appendix — data-pull prompt (for the browser data agent)

> Public sources only — keep CTG out of anything leaguewide/historical (licensing
> guardrail). Save every file untouched to `data/local/raw/<source>/<pull-date>/`
> (one folder for this batch), then it gets `make ingest`ed.
>
> **Pull 1 (priority) — BBref historical leaguewide team stats (Mosley's ORL tenure).**
> For **2024-25** (BBref year 2025), and if easy **2023-24 / 2022-23 / 2021-22**: from
> the BBref league page (e.g. `basketball-reference.com/leagues/NBA_2025.html`), export
> the same six team tables we already have for 2025-26 — Team per-100, Opponent per-100,
> Team shooting (incl. % of FGA by distance = rim/mid/three), Opponent shooting, Team
> ratings, Team advanced — all 30 teams, via each table's "Share & Export → Get table as
> CSV." Save season-suffixed: `league_team_per100_2024-25.csv`, `league_opp_shooting_2024-25.csv`, etc.
> *Unlocks:* public 2-season style trace (Post 5 / Mosley).
>
> **Pull 1b — CTG league team tables, same seasons (private — richer fingerprint).**
> Cleaning the Glass → league-wide **Team Tables** views (all 30 teams per table): Four
> Factors, Shooting Frequency & Accuracy (offense *and* defense), Offense/Defense Context
> (transition vs half-court). For **2024-25** and, if easy, the Mosley-ORL tenure
> (2021-22 → 2023-24). ~5 exports/season. Save season-suffixed under `ctg/<date>/`. These
> are **private** (paid content) — they feed a private-prefix mart, never the public
> companion; only credited aggregates go in posts. *Unlocks:* transition/half-court +
> garbage-time-filtered detail for the Mosley style trace and Analysis F.
>
> **Pull 2 — PBPStats leaguewide per-player shot distribution, both seasons.**
> PBPStats → **Totals → Player** → Season 2024-25 then 2025-26, Regular Season, Stat Type
> Totals, **Table Data: Shot Distribution** → export the full-league table. Save
> `league_player_shotdist_2024-25.csv` / `_2025-26.csv` under `pbpstats/<date>/`.
> Gives per-player AtRimFrequency / AtRimAccuracy + zone frequencies leaguewide.
> *Unlocks:* sharper "lives at rim" + leaguewide shot flags (A/C/D). (Offense only — not rim protection.)
>
> **Pull 3 (easy) — current DARKO (2026-27).** darko.app current leaderboard → Download
> CSV → `darko/<date>/darko-dpm-leaderboard.csv`. *Unlocks:* Post 4 forward-looking
> (reflects offseason, e.g. Vučević→ORL). 2026-27 roster/minutes construction is manual.
>
> **Optional (heavy) — leaguewide 2025-26 2-man + on/off:** same per-team BBref
> lineups+on/off pull as the 2024-25 batch but season 2026, all 30 teams →
> `league_lineups_2man.csv` + `league_onoff.csv`. Only if you want pair-WOWY on 2025-26
> too (ORL/NOP 2025-26 already exist).
>
> Checks: all 30 teams in leaguewide files; season labeled in filename; spot-check one
> value vs the live site.
