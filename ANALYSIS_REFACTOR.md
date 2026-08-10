# Analysis refactor — implementation log

Living record of the 2026 analytical refactor (the "same constraint, different paths" rebuild).
Phases 1–3 are complete; 4–6 (series prose, Mosley, cleanup) are in progress. Findings are
written as they lock, so the eventual Post prose is built on settled evidence.

---

## What changed

**Phase 1 — audit.** Reproduced the pipeline and traced the three data-quality questions the
brief flagged. All three were real defects and are now fixed (below).

**Phase 2 — narrative-enabling data.** Three two-season marts + a sourced transaction history
that let us separate *roster construction* (who was acquired), *roster architecture* (traits that
coexist), and *realized deployment* (co-minutes actually shared) — concepts the old analysis
conflated.

**Phase 3 — statistical cleanup.** Playoff tagging, role-coverage recovery, a calibrated
out-of-fold talent baseline, and robustness batteries on the saturation and fit-feature results.

## New data added

- `mart_star_teammate_context` (16 rows, 2 seasons) — Paolo/Zion co-minutes with each teammate + traits.
- `mart_star_supporting_cast` (4 rows, 2 seasons) — co-minute-weighted realized environment per star-season.
- `mart_availability` (1096 rows, 2 seasons) — games/minutes played & missed + DPM ("availability tax").
- `data/local/manual/transactions_{orl,nop}.csv` (70 / 71 rows, 2019-2026) — sourced construction history.
- `load_transactions()`, `calibrated_fit_residual()` in `_lab.py`.
- `mart_games_styled`: added `is_playoff` / `game_type`.
- `mart_lineup_features_league`: added role-coverage flags (`has_creator/has_shooter/has_rim_protector`,
  `n_shooters/n_creators/n_role_covered`).

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
  `net ~ f(ΣDPM)`, linear and quadratic.

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

## Remaining limitations

- Star-teammate exposure uses BBref 2-man co-minutes (meaningful pairs only); the lowest-exposure
  teammates are absent (near-zero weight anyway).
- Availability `gp` is games-for-this-team (a mid-season arrival looks like an absence); acceptable
  for continuity, flagged for injury interpretation.
- DPM is integer-rounded in every snapshot; the talent baseline is coarse (consistently so).
- Leaguewide star-season generalization (Analysis C) remains n≈20 — underpowered; presented as
  exploratory.

## Recommended next data pull

- (Cowork, in flight) ORL/NOP transaction history — **done**, validated.
- 2024-25 CTG team-style parser → two-season `mart_team_style` (Phase 5 / Mosley).
- Optional: a 2023-24 DARKO snapshot would let us lag 2024-25 talent and fully close the leakage
  question for both seasons.
