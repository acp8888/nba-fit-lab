# NBA "Fit, Quantified" — Build & Learning Plan

**A guided project plan for building an NBA analytics pipeline (S3 → DuckDB → marimo → published research) with an emphasis on learning the tooling, not just shipping it.**

Author context: acp8888 (github.com/acp8888). Publishing: mix of Substack long-form, X threads, Reddit. Published posts are about **NBA analytics only** — the tech stack is invisible to readers. Analysis tone: moderately stats-heavy (lead with findings and charts, one methods paragraph, footnote the details).

---

## Part 0 — Instructions for the AI guiding this project

You (the model reading this) are a **tutor and pair-programmer, not a contractor**. The user has prior S3 experience, is new-ish to DuckDB, marimo, and modern Python project tooling, and explicitly wants to learn. Follow these rules:

1. **Explain → sketch → they write → you review.** For each new concept, give a short explanation of *why it exists*, show a minimal example on toy data, then have the user write the real version themselves. Review their code and point at problems; don't silently rewrite it.
2. **One concept per session.** Don't introduce DuckDB, Parquet, partitioning, and window functions in the same breath. The phase plan below sequences concepts deliberately — respect it.
3. **Checkpoints are mandatory.** Each phase ends with a checkpoint (marked ✅). Before moving on, ask the user to explain the concept back or predict behavior ("what happens if you re-run ingestion for the same date?"). If they can't, revisit — don't proceed.
4. **When they're stuck vs. impatient:** if they're repeating the same wrong idea or shut down, give a foothold — write the first step, narrate why, have them finish. If they just want speed, narrow the hint but keep them writing the last step.
5. **Boilerplate exception:** pure boilerplate (pyproject metadata, .gitignore, GitHub Actions YAML skeletons) you may write outright — it teaches nothing. Anything touching data modeling, SQL, or analysis logic, the user writes.
6. **Keep the blog firewall.** Analysis outputs must be publication-ready and about basketball. Never let pipeline jargon leak into post drafts.
7. **Verify current facts.** Roster/coaching/stat claims in Part 4 were accurate as of July 5, 2026. Before any post is drafted, re-verify against current sources — the offseason moves fast.

---

## Part 1 — Target architecture

```
 BBref / DARKO / PBPStats / NBA.com exports (manual CSV downloads)
        │
        ▼
 ingest/  (Python + boto3)          ── learn: idempotent ingestion, snapshots
        │  writes dated, immutable objects
        ▼
 s3://<bucket>/raw/<source>/<yyyy-mm-dd>/*.csv      (RAW: append-only)
        │
        ▼
 transform/ (DuckDB SQL, httpfs)    ── learn: columnar formats, SQL modeling
        │  staging: typed, cleaned, deduped
        ▼
 s3://<bucket>/staging/*.parquet
        │  marts: analysis-ready tables
        ▼
 s3://<bucket>/marts/*.parquet      (lineup_features, games_styled, player_proj …)
        │
        ▼
 notebooks/ (marimo, .py files)     ── learn: reactive notebooks, sklearn, viz
        │
        ├──► charts/  (static PNG/SVG for Substack + X)
        └──► site/    (marimo WASM export → GitHub Pages interactive companions)
```

Repo name suggestion: `nba-fit-lab` (public — it's part of your credibility; the posts link to it optionally, never depend on it).

Storage decision: real **AWS S3** (user knows it; wants to build properly). One bucket, e.g. `acp-nba-fit-lab`, with `raw/`, `staging/`, `marts/` prefixes. If egress costs ever matter for the public WASM site, mirror `marts/` to Cloudflare R2 later — DuckDB and the site only need a URL change.

---

## Part 2 — Phase plan (with learning objectives, steps, exercises, checkpoints)

Estimated cadence: 1 phase ≈ 2–5 evenings. Phases 0–3 before Post 2; Phase 4 runs alongside the posts.

### Phase 0 — Project foundation (Python tooling done right)

**Learning objectives:** modern Python project layout, `uv`, virtual envs, lockfiles, pre-commit, why notebooks-as-.py matters for git.

Steps:
1. Create the GitHub repo `nba-fit-lab`. Clone locally.
2. Install `uv` (Astral). Initialize with `uv init`, Python ≥3.12. Discuss: what problem do lockfiles solve? Why `uv` over bare pip? (Speed, reproducibility, single tool for envs+deps.)
3. Add dependencies in two groups: core (`duckdb`, `boto3`, `polars` or `pandas`, `pyarrow`) and analysis (`marimo`, `scikit-learn`, `matplotlib`, `altair`, `statsmodels`).
4. Layout:
   ```
   nba-fit-lab/
   ├── pyproject.toml
   ├── src/nba_fit/          # ingestion + shared utils (installable package)
   ├── transform/            # .sql files, numbered: 10_staging_*, 20_marts_*
   ├── notebooks/            # marimo .py notebooks
   ├── data/local/           # gitignored scratch; mirrors S3 layout for offline work
   ├── charts/               # exported figures (gitignored except final post assets)
   └── Makefile              # entry points: make ingest / transform / lab
   ```
5. Set up `pre-commit` with `ruff` (lint+format). Explain what each hook does before enabling it.
6. First commit, sensible `.gitignore` (data, credentials, caches).

Exercise: user writes a `Makefile` with three phony targets that just echo for now; explain `.PHONY`.

✅ **Checkpoint:** user can explain (a) what `uv.lock` pins and why teammates/CI need it, (b) why marimo's .py format beats .ipynb for version control.

### Phase 1 — Raw layer on S3 + ingestion (data engineering fundamentals)

**Learning objectives:** immutable raw zone, dated snapshots, idempotency, manifests, least-privilege IAM, boto3 patterns.

Concepts to teach first (short): why raw is append-only (reprocessability, auditability, "the pipeline is code, the raw data is truth"); why snapshots are dated (DARKO updates daily — point-in-time projections let you later ask "what did the model think on July 5?").

Steps:
1. Create bucket with versioning ON, public access OFF. Create an IAM user/role scoped to this bucket only (user writes the policy JSON; review it — this is the least-privilege exercise).
2. Local layout mirrors S3: files land in `data/local/raw/<source>/<date>/` first, then sync. Teaches the "develop local, promote to cloud" habit.
3. User writes `src/nba_fit/ingest.py`:
   - Takes a source name + list of local files.
   - Computes SHA-256 per file; uploads to `raw/<source>/<yyyy-mm-dd>/<filename>`.
   - Writes/updates a `manifest.jsonl` per source (date, filename, hash, row count).
   - **Idempotent:** re-running for the same date+hash is a no-op; same date+different hash raises loudly (raw is immutable — discuss why erroring beats overwriting).
4. Run first real ingestion using the export shopping list in Part 3.

Exercises:
- Break it on purpose: modify a local CSV and re-run. Watch the hash check fire.
- `aws s3 ls --recursive` and explain the layout to the model.

✅ **Checkpoint:** user explains idempotency and why the manifest exists (answer: lineage — every mart row should be traceable to a raw snapshot).

### Phase 2 — DuckDB transformation layer (the analytical database)

**Learning objectives:** DuckDB as an in-process query engine, reading CSV/Parquet directly from S3 (`httpfs` + secrets), staging→marts modeling, Parquet + partitioning, window functions, data tests.

Concepts to teach first: row vs. columnar storage (why Parquet queries in ms); "no server" model (DuckDB is SQLite-for-analytics); medallion-lite (raw → staging → marts) as separation of *cleaning* from *modeling*.

Steps:
1. Interactive warm-up in the DuckDB CLI: `SELECT * FROM read_csv_auto('data/local/raw/bbref/…/lineups.csv') LIMIT 5;` — no loading step. Let that land.
2. Configure the S3 secret in DuckDB (`CREATE SECRET … TYPE S3`); query the same file from `s3://`. Discuss when to work local vs. remote (local for dev iteration, remote as source of truth).
3. **Staging models** (user writes, one .sql file per table):
   - `stg_lineups`: parse BBref's lineup string into 5 player columns + a sorted key; cast minutes/ratings; tag team + season.
   - `stg_games`: game logs with opponent four factors, home/away, margin, date.
   - `stg_darko`: player, date-of-snapshot, DPM, O-DPM, D-DPM.
   - `stg_pbp_lineups` and `stg_player_shooting` from PBPStats (rim freq, corner-3 rate, 3PA rate).
   - Each staging file ends with 2–3 **assertion queries** (e.g., `SELECT count(*) FROM stg_lineups WHERE minutes < 0` must return 0). This is testing culture without adding dbt yet.
4. **Marts** (the analysis contract):
   - `mart_lineup_features`: one row per lineup-stint aggregate, with engineered fit features — `n_shooters` (players ≥ league-median 3PA rate AND ≥ ~36% on volume, thresholds from staging data, not vibes), `has_rim_protector` (block rate / rim-deter proxy), `n_creators` (self-created shot share or high AST+USG proxy), `spacing_score` (sum of teammates' 3-pt gravity proxies), plus net rating and possessions.
   - `mart_team_style`: one row per NBA team-season: pace, 3PA rate, rim frequency, TOV% forced, OREB%, avg height/size proxy, transition frequency if available. (All 30 teams — needed for clustering.)
   - `mart_games_styled`: Magic/Pelicans game logs joined to opponent style rows.
   - `mart_player_proj`: latest DARKO snapshot joined to roster + per-player fit features.
   - Write marts as Parquet to `s3://…/marts/`, partitioned by season.
5. User writes `transform/run.py` (or Make target) that executes SQL files in numeric order and fails on any assertion violation.

Exercises:
- Window function drill: rolling 10-game net rating per team in `mart_games_styled`.
- Explain to the model why `n_shooters` lives in a mart, not staging (staging = faithful cleanup; marts = opinions/modeling).

✅ **Checkpoint:** user can (a) sketch the raw→staging→mart flow for one column end-to-end, (b) explain why Parquet + partitioning beats one giant CSV, (c) re-run the whole transform from scratch and get identical marts (determinism).

### Phase 3 — marimo analysis environment

**Learning objectives:** reactive dataflow (vs. Jupyter's hidden state), notebook-as-app, parameterized analysis with UI elements, exporting static charts.

Steps:
1. `uv run marimo edit notebooks/00_tour.py` — teach reactivity by demonstration: define `x`, use it in two cells, change it, watch downstream recompute. Contrast with the classic Jupyter stale-state bug.
2. Establish the house pattern: every notebook's first cell connects DuckDB to the S3 marts (or local mirror) and pulls only the tables it needs into dataframes. Notebooks never read raw.
3. Build `notebooks/10_lineup_explorer.py`: dropdown (team), slider (`n_shooters` threshold), reactive table + chart of lineup net rating by shooter count, minutes-weighted. This is both a learning vehicle and the eventual Post 2 companion app.
4. Chart discipline for publishing: one chart = one claim; title states the finding ("Magic lineups with ≤1 shooter: −7.9/100"), not the variables; consistent team colors; export helper that writes 2× PNG + SVG to `charts/`.

✅ **Checkpoint:** user explains why marimo can't have stale state (DAG of cell dependencies) and demos the explorer with the slider live.

### Phase 4 — The four analyses (each powers a post; specs in Part 4)

Each analysis = one marimo notebook + any new mart columns it needs. Order: A2 → A3 → A4 (A1 is narrative and uses only summary stats).

- **A2 — Scarcity regression:** minutes-weighted regression of lineup net rating on `n_shooters`, `has_rim_protector`, `n_creators` (+ interactions), Magic and Pelicans separately, league pooled as a baseline. Teach: weighting by possessions, small-sample honesty (lineup data is noisy — report intervals, consider empirical-Bayes shrinkage toward team mean), and the difference between "statistically significant" and "big enough to matter."
- **A3 — Opponent archetype clustering:** standardize `mart_team_style`, k-means with k chosen by silhouette + interpretability (expect ~4–6: e.g., pace-and-space, rim-pressure, switch-heavy grinders, drop-coverage walls). Then per-cluster average margin and eFG% allowed for ORL/NOP from `mart_games_styled`. Teach: feature scaling, why k-means needs it, cluster stability (re-run with seeds), and naming clusters by centroid inspection.
- **A4 — Roster-delta projection:** minutes-allocation model (user drafts depth-chart minutes; sanity-check vs. last season), DARKO DPM → team point differential → pythagorean wins. Then the novel layer: adjust for fit using A2 coefficients (e.g., if projected closing lineups clear the shooting threshold that last year's didn't, credit the interaction, transparently and conservatively). Teach: propagating uncertainty (simulate minutes/DPM draws → win distribution, not a point estimate).
- **A5 (optional, in-season) — Fit tracker:** weekly refresh via GitHub Actions (cron → ingest new exports is still manual, but transforms + site rebuild automate). Teaches CI/CD on real infrastructure.

### Phase 5 — Publishing pipeline

1. `marimo export html-wasm notebooks/10_lineup_explorer.py -o site/` — self-contained, Python-in-browser.
2. Ship the small Parquet marts the notebook needs alongside the site (or public-read `marts/` prefix / R2 mirror); confirm the WASM app loads them over HTTP.
3. GitHub Pages from `site/` via a GitHub Actions workflow (boilerplate exception: model may write the YAML; user must be able to read it line-by-line).
4. Per-post asset checklist: hero chart (PNG 2×), 2–3 supporting charts, one methods footnote block, link to interactive companion, 6–10 tweet thread skeleton pulling the same charts.

✅ **Final checkpoint:** a stranger can go export-fresh-CSVs → `make ingest transform` → open notebook → export site, following only the README.

---

## Part 3 — Data export shopping list (repeat per team; ~30 min)

| Source | What to export | Feeds |
|---|---|---|
| Basketball-Reference team pages (ORL 2026, NOP 2026) | Lineups (5-man & 2-man), On/Off, Advanced game log, Team & opponent shooting | stg_lineups, stg_games |
| Basketball-Reference league pages | 2025-26 team ratings + team/opponent per-100 + shooting for **all 30 teams** | mart_team_style |
| DARKO (apanalytics.shinyapps.io/DARKO) | Current DPM table (full league), CSV download; snapshot dated | stg_darko |
| PBPStats.com | Lineup exports for ORL/NOP; player shot-profile exports (rim freq, corner 3s, 3PA rate) league-wide if feasible | fit features |
| NBA.com/stats (manual) | Anything missing above (e.g., tracking touches) — optional | enrichment |

Convention: every downloaded file goes to `data/local/raw/<source>/<yyyy-mm-dd>/` untouched (original filename kept), then `make ingest`.

---

## Part 4 — Blog post sequence (basketball-facing; tech invisible)

Context that frames the whole series (verify before publishing — see Part 0 rule 7):
- Magic 2025-26: 45-37, 8th in the East, offense 19th (114.9) vs. defense 11th (114.3), 27th in 3P% (34.3) — a year after trading four unprotected firsts plus a swap for Desmond Bane to fix exactly that. Led Detroit 3-1 in round one, lost in seven, including a Game 6 where they blew a 24-point lead and missed 23 straight shots. Fired Jamahl Mosley; hired Sean Sweeney; brought back Vučević on a one-year minimum-level deal.
- Pelicans 2025-26: 26-56, Willie Green fired after 1-12, Borrego interim, then hired… Mosley, on a five-year deal. Zion stayed healthy-ish (62 games, ~21 ppg) and Dumars says he's staying. Zion+Queen lineups were −11 per 100 (no spacing, no rim protection); Borrego benched the pairing by late February. Fears/Dejounte Murray overlap in the backcourt. Trey Murphy trade rumors persist (reported ask: three firsts). No 2026 first-rounder (spent on Queen).

**Post 1 — "One coach, two broken rosters."** (Narrative; needs only summary stats.) Thesis: Orlando and New Orleans are the league's two purest *fit* failures — top-heavy talent, bottom-tier complementarity — and the Mosley swap makes them a natural experiment: if fit is mostly coaching, Mosley's Pelicans improve and Sweeney inherits Orlando's ceiling problem; if fit is mostly roster, both franchises repeat their seasons with new sideline scapegoats. Set up the series' measurable predictions so later posts can grade them. *Analysis needed:* summary table of both teams' four factors + the two signature stats (27th in 3P%; −11/100 Zion+Queen).

**Post 2 — "The spacing threshold."** (From A2.) Finding format: "Below X shooters on the floor, Magic lineups lose by Y per 100; above it they're a top-Z offense — and they played N% of their minutes below the threshold." Same structure for New Orleans with the rim-protection interaction. This post explains *why* the Bane trade underdelivered at team level: one elite shooter next to two non-spacing 6'10" creators doesn't clear the threshold; shooter #2 is worth more than shooter #1 was. Interactive companion: the lineup explorer. *Reddit angle:* "The Magic's problem was never Bane — it's that he was their only shooter."

**Post 3 — "Know your enemy: what kind of team beats the Magic (and who the Pelicans can actually punish)."** (From A3.) Present the 4–6 league archetypes with names readers can use, then each team's margin vs. each archetype. Case study: Detroit as Orlando's nightmare archetype and how the Game 6 collapse was the season's thesis in miniature. For NOP: which archetypes their young core already competes with, and what that says about the build. *Thread angle:* one chart — archetype grid with win% cells.

**Post 4 — "The moves that actually matter."** (From A4.) Projected win distributions for both teams as currently constructed; then the marginal-value rankings: best realistic *addition* by fit-adjusted impact (hypothesis to test: a second high-volume shooter moves Orlando more than any other archetype, including a better backup center), and most damaging *subtraction* (hypothesis: trading Trey Murphy costs New Orleans far more than his DARKO value implies, because he's the lone elite spacer holding lineups above the threshold). Grade real offseason moves as they happen. Time for late offseason / camp.

**Post 5 — "Same coach, new roster: the Mosley experiment, first returns."** (In-season, ~20 games.) Grade Post 1's predictions with A5's tracker: Pelicans' fit metrics under Mosley vs. last season, Magic's under Sweeney. This is the series' payoff and the strongest recurring-audience hook.

**Post 6+ — spin-offs as material allows:** "Fears + Queen: building around the kids' fit profile, not their box scores." / "What archetype should the Magic pray to face in April?" (playoff-seeding matchup piece). / Trade-deadline live application of the A4 engine to real rumors.

---

## Part 5 — Milestones & definition of done

- **M1 (Phase 0–1 done):** repo public, first raw snapshot on S3, README explains layout. 
- **M2 (Phase 2 done):** `make transform` builds all marts from S3, assertions pass, deterministic re-runs.
- **M3 (Phase 3 done):** lineup explorer works locally; first exported chart meets the chart-discipline rules.
- **M4:** Post 1 published; Post 2 analysis notebook reviewed (model reviews stats honesty: weighting, intervals, shrinkage).
- **M5:** Interactive companion live on GitHub Pages; Post 2 published linking it.
- **M6:** Posts 3–4 published; Actions-based weekly rebuild running for the in-season tracker.

Stretch (only after M6, and only if wanted): dbt or SQLMesh over the transform layer, dlt for ingestion, DuckLake/Iceberg table formats, Evidence.dev as an alternative publishing surface. These are résumé-relevant but not needed — introduce each by asking "what pain from our current setup does this remove?"
