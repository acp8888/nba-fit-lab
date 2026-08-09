# Marts reference

Analysis-ready tables published to S3 by the transform layer. Read any mart with:

```python
duckdb.sql("select * from read_parquet('s3://nba-fit-lab/marts/<name>/**/*.parquet')")
# or in a notebook:  from _lab import load_mart;  load_mart("<name>")
```

`season` is recovered from the hive partition path (`season=YYYY`; **2025 = the 2024-25
season, 2026 = 2025-26**). **Season coverage is uneven:** `mart_player_league`,
`mart_availability`, `mart_star_teammate_context`, and `mart_star_supporting_cast` span
**both** seasons; `mart_pair_synergy` is **2024-25 only**; every other mart is **2025-26 only**.
Cross-season work otherwise goes through the `_lab` loaders (below).

| mart | grain | rows | season | in one line |
|---|---|---|---|---|
| `mart_team_style` | team | 30 | 2026 | each team's pace/size/shot-profile fingerprint (CTG-rich) |
| `mart_games_styled` | ORL/NOP game | 171 | 2026 | per-game result + opponent quality & style |
| `mart_lineup_features_league` | leaguewide 5-man lineup | 600 | 2026 | the fit-regression workhorse (net vs talent + fit features) |
| `mart_lineup_features` | ORL/NOP 5-man lineup | 40 | 2026 | ORL/NOP lineups with *discrete* fit flags |
| `mart_pair_synergy` | 2-man pair | 556 | **2025** | pairwise WOWY complementarity + trait overlaps |
| `mart_player_proj` | ORL/NOP player | 20 | 2026 | rich CTG per-player profile + archetype flags |
| `mart_player_league` | leaguewide player | 600 | **2025+2026** | per-player archetype percentiles + flags, both seasons |
| `mart_roster` | leaguewide player | 581 | 2026 | player DPM + minutes (projection-engine input) |
| `mart_star_teammate_context` | season×team×star×teammate | 16 | **2025+2026** | Paolo/Zion co-minutes with each teammate + that teammate's traits |
| `mart_star_supporting_cast` | season×team×star | 4 | **2025+2026** | the realized (co-minute-weighted) environment each star actually played in |
| `mart_availability` | season×team×player | 1096 | **2025+2026** | games/minutes played + games missed + DPM (the "availability tax") |

*(Two junk tables `_probe_singlefile` / `_write_probe` also sit under `marts/` — stray
write-test artifacts; ignore them. The put-only IAM role can't delete them.)*

---

## `mart_team_style` — 30 rows, one per team · 2025-26
Team "style fingerprint" (CTG-rich, garbage-time filtered): `pace`, `size_wavg_height_in`;
full offense (`off_rim_rate`, `off_short/long_mid_rate`, `off_corner/non_corner_three_rate`,
`off_three_pa_rate`, `off_transition_rate`, `off_transition_ppp`, `off_halfcourt_ppp`); full
defense (`def_rim_rate_allowed`, `def_three_pa_rate_allowed`, `def_tov_forced_pct`,
`def_orb_allowed_pct`, `def_transition_*`); four factors; `off/def/net_pts_poss`.

**Informs:** team archetype clustering (found: fuzzy, no clean types); opponent-style
features; Mosley style trace (2-season version not yet built — see loaders/open threads).

## `mart_games_styled` — 171 rows, one per ORL/NOP game · 2025-26
Per-game outcome (`margin`, `o/d/net_rtg`, `result`, `pace`, `three_pa_rate`,
`off_efg_pct`, `rolling_10_net_rtg`, `is_away`) joined to the **opponent's** season quality
(`opp_net_pts_poss`) and style (`opp_off_rim_rate`, `opp_def_three_pa_rate_allowed`, …).

**Informs:** process-vs-outcome (style bends *how* you play, not *whether* you win);
home-court value (~+4); swing games / over-underperformance; close-game & clutch analysis.

## `mart_lineup_features_league` — 600 rows, one per leaguewide top-~20 5-man lineup · 2025-26
The fit workhorse: `net_pts_per100`, `talent_sum_dpm` (ΣDPM), `fit_residual` (net − talent);
three spacing measures (`spacing_mean` = 3PA rate, `spacing_gravity_mean` = CTG,
`spacing_cs_mean` = NBA catch-&-shoot); rim protection (`rim_suppress`, `opp_rim_freq`,
`opp_rim_acc`, `rim_max_blk`); size (`avg_height_in`, `tallest_in`); `usg_max`, `usg_spread`,
`ast_max`. Has `lineup_key` (`|`-joined sorted "F. Last") but not player columns.

**Informs:** the core fit regression; talent saturation (pool with `load_5man_features_2024`).
**Established:** talent dominates *and saturates* (net is concave in ΣDPM); rim protection is
the one fit lever; spacing is a null; the size penalty is fragile.

## `mart_lineup_features` — 40 rows, ORL/NOP top-~20 lineups · 2025-26
CTG-rich ORL/NOP-only version with **discrete** fit flags: `n_shooters`, `n_creators`,
`has_rim_protector`, `spacing_score` + `net_pts_per100` and `player_1..5`.

**Informs:** ORL/NOP lineup deep-dives; the original "spacing threshold" angle.

## `mart_pair_synergy` — 556 rows, one per 2-man pair · **2024-25**
WOWY pairwise complementarity: `complement` / `complement_centered` (within-team),
`together_net`, `talent_sum`; trait-overlap features `usg_min` (both ball-dominant),
`csg_min`/`csg_max` (spacing redundancy), `cross_cs` (creator×spacer), `height_min`,
`blk_min`/`blk_max` (rim redundancy), `usg_gap`. Keyed (team, player_a, player_b).

**Informs:** pairwise diminishing returns. **Established:** trait redundancy doesn't hurt
(perimeter overlaps null; only interior/rim pays) — the "two ball-handlers can't coexist"
myth doesn't survive.

## `mart_player_league` — 600 rows (~300/season), leaguewide rotation players · **2024-25 + 2025-26**
Per-player archetype profile, both seasons, from public data (BBref advanced + NBA.com shot
types + PBPStats rim + DARKO). Rotation = MP ≥ 800. Keyed (season, `team` [BBref], `player_name`).
- **Raw traits:** `usg`, `three_pa_rate`, `ast_pct`, `ts_pct`, `blk_pct`, `ast_to_usg`,
  `cs_gravity` (catch-&-shoot floor-spacing), `rim_freq` / `rim_acc` (share of shots at rim +
  FG% there), `dpm`, `height_in`.
- **Within-season league percentiles:** `usg_pctl`, `tpar_pctl`, `csg_pctl`, `ast_pctl`,
  `ts_pctl`, `blk_pctl`, `dpm_pctl`, `rim_freq_pctl`.
- **Tunable archetype flags:** `is_ball_dominant_nonshooter` (usg≥80 & 3PAr≤40 & C&S≤40 pctl —
  the Banchero/Williamson star archetype; flags ~22 leaguewide stars), `is_shooter` (C&S≥60
  pctl), `is_creator` (usg≥24 or ast:usg≥1.15), `is_rim_protector` (BLK%≥75 pctl & height≥82in
  — a BLK+size **proxy**, since true rim on/off is CTG/ORL-NOP-only).

**Informs:** Post 1 star fingerprints + the duplicate-vs-complement inversion; Analysis C
(leaguewide generalization); role coverage (Post 2 capstone). **Established:** the inversion
holds at the wing, breaks at center; complement builds weakly over-perform talent (pooled
n=20, underpowered); role coverage is a null (coaches pre-empt the cliffs).

## `mart_player_proj` — 20 rows, ORL/NOP rotation players · 2025-26
Rich CTG per-player profile: `dpm/o_dpm/d_dpm`; shot **frequency + accuracy by zone**
(`freq_rim…freq_three`, `acc_rim/midrange/three`); `usage`, `ast_pct`, `ast_to_usg`,
`tov_pct`, `psa`; on/off (`net_on_off`, `rim_onoff_diff`, `rim_onoff_pctile`); archetype flags
`is_shooter/is_creator/is_rim_protector`. *(The ORL/NOP-detail cousin of
`mart_player_league`; richer CTG fields but only 2 teams.)*

## `mart_roster` — 581 rows, one per player leaguewide · 2025-26
`player_name`, `team` (BBref), `team_name` (full), `position`, `dpm/o_dpm/d_dpm`, `mpg`.

**Informs:** roster win projections (backtest); team talent sums; leaguewide DPM leaderboards.

## `mart_star_teammate_context` — 16 rows, (season, team, star, teammate) · **2024-25 + 2025-26**
The **realized deployment** table: for each star (Paolo, Zion) and each teammate they actually
shared the floor with, `shared_min` (BBref 2-man co-minutes), `star_oncourt_min` (BBref on/off),
`pct_star_min_shared`, plus the teammate's fit traits from `mart_player_league`
(`tm_dpm`, `tm_usg`, `tm_csg_pctl`, `tm_tpar_pctl`, `tm_rim_freq_pctl`, `tm_height_in`,
`tm_is_shooter/creator/rim_protector`). Season sources differ (leaguewide 2-man/on-off for
2024-25; team-specific `orl_/nop_` files for 2025-26). Answers *"who did the star play with,"*
not *"who was on the roster."*

**Informs:** Post 1 (roster architecture vs realized environment) and Post 3 (the ORL/NOP
decomposition). **Established:** in 2025-26 Zion's top-two co-minute teammates (Murphy C&S 82,
Bey 69) are strong shooters — the star was not "starved" of spacing.

## `mart_star_supporting_cast` — 4 rows, (season, team, star) · **2024-25 + 2025-26**
The star-season **realized-environment fingerprint**, co-minute-weighted from
`mart_star_teammate_context`: `star_oncourt_min`; `cast_dpm` (talent of the teammates the star
actually played with), `cast_csg_pctl` (their spacing), `cast_rimf_pctl`, `cast_height_in`; and
coarse counts `n_shooters_hi / n_creators_hi / n_rimprot_hi / n_teammates_hi` (distinct
teammates sharing ≥25% of the star's minutes). Continuous measures are robust; the counts are
directional (binary flags).

**Informs:** the **continuous** overlap↔complementarity axis that replaces the binary
duplicate/complement label (§9). **Established:** Paolo's and Zion's 2025-26 co-minute spacing
environments are nearly identical (50 vs 49); the difference that matters is availability
(`star_oncourt_min`: Paolo 1583→2514 vs Zion 859→1842).

## `mart_availability` — 1096 rows, (season, team, player) · **2024-25 + 2025-26**
Leaguewide player availability: `gp`, `team_games` (82), `games_missed`, `pct_games_avail`,
`mp`, `mpg`, `dpm`, `is_rotation` (MP≥800). Source: BBref Advanced `G`/`MP` per team-stint
(a mid-season trade splits a player into two rows, so `gp` is games-for-THIS-team — low `gp`
can mean "arrived late," not "hurt"); DARKO for `dpm` (joined name+season, so trades resolve).
The **availability tax** (e.g. `Σ greatest(dpm,0) · games_missed`) is a notebook-level
computation, kept out of the mart so the weighting stays an explicit, documented choice.

**Informs:** Post 3 (why NOP collapsed) and the projection backtest's injury-driven misses.
**Established:** NOP 2024-25 lost the 7th-most DPM-weighted games in the league (Zion 30 GP,
Murray 31 GP) — the collapse was largely an availability shock; NOP 2025-26 was among the
*healthiest* teams (rank 26), so that season's weakness is talent (−5.5), not health.

---

## Non-mart loaders (via `notebooks/_lab.py`)

Deliberate raw-reading exceptions to "notebooks read marts" — for cross-season/forward data
that isn't a published mart.

- **`load_5man_features_2024()`** — same schema as `mart_lineup_features_league`, the **2024-25**
  held-out season (rebuilt from raw). → replication + pooled talent-saturation.
- **`load_games_rim()`** — **per-game** rim (opponent + own at-rim) for ORL/NOP, 2025-26. →
  per-game fit-win/loss / clutch.
- **`load_team_seasons()`** — per (season, team) actual net (BBref NRtg) + talent (5× wmean DPM),
  **both** seasons. → the pooled Analysis C.
- **`load_roster_2027()`** — **2026-27** projected rosters (team, player, dpm, mpg) from DARKO's
  preseason leaderboard. → Post 4 forward-looking. CAVEAT: preseason DPM is integer-rounded and
  regressed to the mean; DARKO's rosters miss some July moves (e.g. Vučević→ORL not booked).
- **`load_transactions()`** — ORL+NOP **roster-construction history** (70 ORL / 71 NOP rows,
  2019-2026) from hand-curated, source-cited CSVs at `data/local/manual/transactions_{orl,nop}.csv`
  (public data, version-controlled). One row per player per side of a move; adds an `era` tag
  (`pre_star`/`post_star`) relative to the star's draft (Zion 2019-06-20 / Paolo 2022-06-23). →
  Post 1 construction timeline. NEUTRAL: `era` is timing, not inferred front-office intent.

---

## Notes for downstream analysis

- **Grain differs** across marts — mind join keys ("F. Last" for lineups, full name → "f. last"
  fold for players, full team name vs BBref code).
- **DPM is integer-rounded** in every DARKO snapshot → the talent baseline is coarse (consistent
  across seasons, so comparisons are fair).
- **Marts are opponent-*averaged*, not adjusted**, and lineups are each team's ~top-20 by minutes
  (a pre-optimized, range-restricted slice).
- **Biggest lead already spent:** role-coverage (does a lineup *missing a role* fail?) was tested
  on `mart_player_league` flags and came back **null** — coaches deploy a creator in 99% of
  lineups and a spacer in 98%, so the cliffs never appear. Reported as the Post 2 capstone.
- **Not yet built:** a **2-season `mart_team_style`** (Mosley style fingerprint / Post 5) — the
  2024-25 CTG raw is a rawer, verbose format than the pre-cleaned 2025-26 files, so it needs a
  2024-25-specific CTG parser across 9 files.
