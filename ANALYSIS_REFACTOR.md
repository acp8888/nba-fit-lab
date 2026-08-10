# Analysis refactor — implementation log

Record of the 2026 analytical refactor (the "same constraint, different paths" rebuild). All six
phases are complete. Findings were written as they locked, so the Post prose is built on settled
evidence. The five-post narrative lives in `notebooks/walkthrough.py`; the data map in `MARTS.md`.

---

## What changed

**Phase 1 — audit.** Reproduced the pipeline and traced the three data-quality questions the
brief flagged. All three were real defects and are now fixed (below).

**Phase 2 — narrative-enabling data.** Three two-season marts + a sourced transaction history
that let us separate *roster construction* (who was acquired), *roster architecture* (traits that
coexist), and *realized deployment* (co-minutes actually shared) — concepts the old analysis
conflated.

**Phase 3 — statistical cleanup.** Playoff tagging, role-coverage recovery, a calibrated
out-of-fold talent baseline, and robustness batteries on the saturation and fit-feature results
(including an independent-talent-measure cross-check via private ShotQuality RAPM).

**Phase 4 — series rebuild.** Full rewrite of `walkthrough.py` around the new thesis: Post 1
(same constraint, different paths), Post 2 (minimum-viable vs marginal fit), Post 3 (why ORL
survived / NOP collapsed — a per-season decomposition), Post 4 (honest backtest + minute-neutral
sims). Every §34 overclaim audited and softened; the opponent-style/matchup work preserved as a
standalone notebook rather than deleted.

**Phase 5 — Mosley.** Parsed the 2024-25 CTG verbose export into a harmonized two-season
`mart_team_style`; fingerprinted Mosley's Orlando; froze pre-registered 2026-27 predictions.

**Phase 6 — sweep.** Full reproducibility rebuild (30 tables, all assertions pass), this document
finalized, a §34/§35 overclaim + season-hygiene audit across both notebooks, and assertion-coverage
confirmation (every mart carries 5–16 `-- ASSERT` checks).

## New data added

- `mart_star_teammate_context` (16 rows, 2 seasons) — Paolo/Zion co-minutes with each teammate + traits.
- `mart_star_supporting_cast` (4 rows, 2 seasons) — co-minute-weighted realized environment per star-season.
- `mart_availability` (1096 rows, 2 seasons) — games/minutes played & missed + DPM ("availability tax").
- `data/local/manual/transactions_{orl,nop}.csv` (70 / 71 rows, 2019-2026) — sourced construction history.
- `load_transactions()`, `calibrated_fit_residual()` in `_lab.py`.
- `mart_games_styled`: added `is_playoff` / `game_type`.
- `mart_lineup_features_league`: added role-coverage flags (`has_creator/has_shooter/has_rim_protector`,
  `n_shooters/n_creators/n_role_covered`).
- `mart_team_style`: extended to **two seasons** (60 rows) by parsing the 2024-25 CTG verbose
  export and harmonizing to the 2025-26 schema. **Private (CTG-licensed).**
- `load_team_seasons()`: added actual `wins`/`losses` (for the backtest). `load_roster_2027()`:
  applies `data/local/manual/roster_2027_overrides.csv`. `load_shotquality()`: **private/local-only**
  ShotQuality RAPM for the independent-talent cross-check.
- `analysis/mosley_predictions_2027.yaml` — pre-registered, frozen Mosley style predictions.

## Analyses rebuilt

- **Role-coverage sample (600→413 bug).** The null was measured by joining lineup players to the
  MP≥800 rotation mart, silently dropping 182 lineups whose fringe fifth man fell below the cut —
  and those lineups were systematically *worse* (mean net −0.4 vs +3.3, 45 vs 73 min). Fixed by
  computing role flags over the full lineup-player population inside the mart: now **595/600**
  fully role-covered. The range-restriction finding **replicates on the unbiased sample**
  (creator present 96%, shooter 93%).
- **171-game sample.** 7 ORL playoff games were mixed in untagged (`game_num` resets 82→1 at the
  postseason). Now tagged; a regular season is exactly 82 games/team.
- **Calibrated talent baseline (§12).** Replaced the implicit "fit = net − ΣDPM" (which assumes a
  talent coefficient of exactly 1) with an out-of-fold (leave-one-team-out) residual from
  `net ~ f(ΣDPM)`, linear and quadratic. (Result: corr 1.00/0.99 with the naive residual — the
  naive version wasn't distorting conclusions, and rim survives the calibrated baseline.)
- **Projection backtest (Post 4).** Rebuilt as an honest all-league backtest (60 team-seasons,
  two steps: talent→net, net→wins). End-to-end **MAE ~6 wins** (not "a couple"); the biggest
  misses are injuries (PHI '25, NOP '25), so the error lives in the talent→net step — the
  projection's own errors *are* the availability story. Roster-move sims made **minute-neutral**
  (value = talent difference the swap creates), with version-controlled 2026-27 roster overrides.
- **Two-season `mart_team_style` (Post 5).** The 2024-25 CTG *verbose* format (full-label columns,
  interleaved rank columns, city short-names, `Average` row) parsed and harmonized to the 2025-26
  schema; units verified consistent across seasons. Exposed a latent double-join bug in
  `mart_games_styled` (now season-pinned), caught by assertions.

## Conclusions that survived

- **Talent saturation / concavity is robust.** Net is concave in ΣDPM pooled (quad p=.001), and in
  2024-25 (p=.001) *and* 2025-26 (p=.025) separately. Quadratic beats linear and cubic on held-out
  leave-one-team-out MSE (15996 < 16211, 16022). **Survives trimming extreme lineups** (5–95%:
  p=.003; 10–90%: p=.015) — not a tail artifact. **Not a same-season DPM leakage artifact**: on
  returning-player lineups, prior-season and same-season DPM give the same result.
- **Rim protection is the one robust fit lever.** ~+4.7 net per SD (p<.05) under naive, linear-
  calibrated, and quadratic-calibrated baselines, and +4.5/SD (p<.001) against a *prior-season*
  talent baseline. **Survives a methodologically independent talent measure**: +3.86/SD off a
  DPM baseline vs +3.81/SD off a **ShotQuality RAPM** baseline (corr of the two talent sums only
  0.61), both p<.001. (Caveat carried forward: `rim_suppress` is opponent rim defense, a slice of
  net, so part of the coefficient is mechanical.)
- **Spacing is null at the margin** after talent (+0.5/SD, n.s.) — but see the reframe below.

## Conclusions that weakened / gained nuance

- **"Diminishing returns" is a globally decelerating curve, not a plateau at the top.** Among
  above-median-talent lineups the concavity is undetectable (quad p=.80) and the *linear* slope
  collapses to +0.41 (vs +1.39 full-sample). So marginal returns to lineup talent among already-good
  lineups are ~30% of the overall slope — real deceleration, but the correct wording is "returns
  flatten sharply among high-talent lineups," **not** the causal overclaim "adding a star gives
  almost nothing."
- **Same-season DPM does carry within-season information** (corr with prior-season talent = 0.76,
  not ~0.95). It doesn't change the saturation or rim conclusions, but it means DPM-based talent is
  not a clean pre-season instrument. Documented, not "fixed" (only a prior-season lag exists, and
  only for 2025-26 — no 2023-24 snapshot to lag 2024-25).
- **Talent saturation is talent-MEASURE-dependent — the important new caveat.** The concavity is
  robust *through the DPM lens* (pooled two-season p=.001, trimmed, binned). But it does **not**
  replicate on an independent **ShotQuality RAPM** talent axis for 2025-26 alone (quad p=.67; DPM
  on the same single-season 561-lineup subset is only p=.07). So "diminishing returns to lineup
  talent" is well-supported in the multi-season DPM data but not confirmed by a second, genuinely
  independent talent measure in a single season — it may partly reflect DPM's own regressed/bounded
  construction. Present with caution; do not state it as a hard basketball law.

## Conclusions that changed

- **Duplicate-vs-complement is not the spine.** On co-minute-weighted realized environments,
  Paolo's and Zion's 2025-26 spacing casts are nearly identical (C&S pctl 50 vs 49; in 2024-25
  Zion's was *better*, 66 vs 20). Descriptively (n=4), better realized spacing does **not** track
  overperformance — NOP 2024-25 had the best spacing cast (66) and the worst outcome (−10.5 vs
  talent). Demoted to exploratory; replaced by the availability/continuity story.
- **NOP's collapse was 2024-25, an availability shock** (talent +0.9 → actual −9.6; 7th-most
  DPM-weighted games lost; Zion 30 GP, Murray 31 GP). NOP 2025-26 was among the *healthiest* teams
  and played to a genuinely −5.5-talent roster — a talent story, not a fit story. The two seasons
  are different problems and must not be pooled into one "NOP failed" claim.

## New conclusions

- **The right frame for spacing is minimum-viable vs marginal fit.** Coaches field a creator in
  96% and a shooter in 93% of deployed lineups (unbiased sample), so catastrophic role-deficient
  lineups barely enter observation. The spacing null is a statement about the *already-functional*
  range NBA coaches deploy, not about spacing being unimportant.
- **The ORL−NOP gap decomposes into two different seasons.** 2024-25: near-equal talent, ~9.5-net
  outcome gap (~20+ wins) that talent doesn't explain → an availability shock. 2025-26: talent
  explains *more* than the whole gap → NOP was simply a low-talent roster. There is no single
  "NOP failed" story; there are two, and neither is about fit.
- **Moves are worth their talent; the fit premium rounds to zero — except rim.** Minute-neutral
  sims put a same-talent shooter-for-non-shooter swap at ≈ 0 extra wins; only a same-talent rim
  protector carries a small positive residual. So "how much talent should you trade for fit?" →
  very little, except for rim protection.
- **Mosley's Orlando signature is defensive and persistent.** Elite opponent-3PA-rate suppression
  (0th/10th percentile across *both* his seasons); pace is explicitly *not* a signature (3rd→60th).
  Frozen, both-directions predictions for 2026-27 in `analysis/mosley_predictions_2027.yaml`.

## Remaining limitations

- Star-teammate exposure uses BBref 2-man co-minutes (meaningful pairs only); the lowest-exposure
  teammates are absent (near-zero weight anyway).
- Availability `gp` is games-for-this-team (a mid-season arrival looks like an absence); acceptable
  for continuity, flagged for injury interpretation.
- DPM is integer-rounded in every snapshot; the talent baseline is coarse (consistently so).
- Leaguewide star-season generalization (Analysis C) remains n≈20 — underpowered; presented as
  exploratory. The ORL/NOP decomposition is a 2-team, 2-season accounting, not a causal identification.
- The projection backtest is ~6-win MAE, so single-team win projections are ranges; preseason DPM
  is integer-rounded and regressed.
- Post 5 is pre-registration only — no 2026-27 games yet to grade the frozen predictions.
- `mart_pair_synergy` is one season (2024-25); presented as supporting, not law.

## Recommended next data pull

- **2026-27 in-season team-style refreshes** — to grade `mosley_predictions_2027.yaml` (the one
  live, forward-looking test left).
- **A 2023-24 DARKO snapshot** — would let us lag 2024-25 talent and fully close the same-season
  DPM-leakage question for *both* seasons (currently closeable only for 2025-26).
- **Leaguewide multi-season games** — to upgrade the standalone matchup analysis beyond its
  one-season ORL/NOP sample (with team × opponent-style interactions).
- (Done) ORL/NOP transaction history; 2024-25 CTG team-style parser; ShotQuality RAPM cross-check.
