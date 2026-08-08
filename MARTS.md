# Marts reference

Analysis-ready tables published to S3 by the transform layer. Read any mart with:

```python
duckdb.sql("select * from read_parquet('s3://nba-fit-lab/marts/<name>/**/*.parquet')")
# or in a notebook:  from _lab import load_mart;  load_mart("<name>")
```

`season` is recovered from the hive partition path (`season=YYYY`). **Season coverage is
uneven:** everything is `2026` (the 2025-26 season) **except** `mart_pair_synergy` (2024-25)
and the held-out loader (2024-25). Cross-season claims currently exist only for lineup
features (via the loader) and pairs.

| mart | grain | rows | season | in one line |
|---|---|---|---|---|
| `mart_team_style` | team | 30 | 2026 | each team's pace/size/shot-profile fingerprint |
| `mart_games_styled` | ORL/NOP game | 171 | 2026 | per-game result + opponent quality & style |
| `mart_lineup_features_league` | leaguewide 5-man lineup | 600 | 2026 | the fit regression workhorse (net vs talent + fit features) |
| `mart_lineup_features` | ORL/NOP 5-man lineup | 40 | 2026 | ORL/NOP lineups with *discrete* fit flags |
| `mart_pair_synergy` | 2-man pair | 556 | **2025** | pairwise WOWY complementarity + trait overlaps |
| `mart_player_proj` | ORL/NOP player | 20 | 2026 | rich per-player profile + archetype flags |
| `mart_roster` | leaguewide player | 581 | 2026 | player DPM + minutes (projection engine input) |

---

## `mart_team_style` — 30 rows, one per team · 2025-26
Team "style fingerprint": `pace`, `size_wavg_height_in`; full offense (`off_rim_rate`,
`off_short/long_mid_rate`, `off_corner/non_corner_three_rate`, `off_three_pa_rate`,
`off_transition_rate`, `off_transition_ppp`, `off_halfcourt_ppp`); full defense
(`def_rim_rate_allowed`, `def_three_pa_rate_allowed`, `def_tov_forced_pct`,
`def_orb_allowed_pct`, `def_transition_*`); four factors; `off/def/net_pts_poss`.

**Informs:** team archetype clustering (found: fuzzy, no clean types); who plays
fast/small/rim-heavy; style fingerprints (Post 1); opponent-style features; league-relative
comparisons.

## `mart_games_styled` — 171 rows, one per ORL/NOP game · 2025-26
Per-game outcome (`margin`, `o/d/net_rtg`, `result`, `pace`, `three_pa_rate`,
`off_efg_pct`, `rolling_10_net_rtg`, `is_away`) joined to the **opponent's** season quality
(`opp_net_pts_poss`) and style (`opp_off_rim_rate`, `opp_def_three_pa_rate_allowed`,
`opp_pace`, …).

**Informs:** process-vs-outcome (style bends *how* you play, not *whether* you win);
home-court value (~+4); swing-game / over-underperformance; close-game & clutch analysis;
schedule strength; form trends.

## `mart_lineup_features_league` — 600 rows, one per leaguewide top-~20 5-man lineup · 2025-26
The fit workhorse: `net_pts_per100`, `talent_sum_dpm` (ΣDPM), `fit_residual` (net − talent);
three spacing measures (`spacing_mean` = 3PA rate, `spacing_gravity_mean` = CTG,
`spacing_cs_mean` = NBA catch-&-shoot); rim protection (`rim_suppress`, `opp_rim_freq`,
`opp_rim_acc`, `rim_max_blk`); size (`avg_height_in`, `tallest_in`); `usg_max`, `usg_spread`,
`ast_max`.

**Informs:** the core fit regression; talent saturation (pool with the 2024-25 loader);
which fit features pay. **Established:** talent dominates *and saturates*; rim protection is
the one fit lever; spacing is a null; size penalty is fragile.

## `mart_lineup_features` — 40 rows, ORL/NOP top-~20 lineups · 2025-26
The CTG-rich ORL/NOP-only version with **discrete** fit flags: `n_shooters`, `n_creators`,
`has_rim_protector`, `spacing_score` + `net_pts_per100`.

**Informs:** threshold effects ("below N shooters, lineups crater") — the original "spacing
threshold" post angle; ORL/NOP lineup deep-dives.

## `mart_pair_synergy` — 556 rows, one per 2-man pair · **2024-25**
WOWY pairwise complementarity: `complement` / `complement_centered` (within-team),
`together_net`, `talent_sum`; trait-overlap features `usg_min` (both ball-dominant),
`csg_min`/`csg_max` (spacing redundancy), `cross_cs` (creator×spacer), `height_min`,
`blk_min`/`blk_max` (rim redundancy), `usg_gap`.

**Informs:** pairwise diminishing returns; best/worst duos. **Established:** trait redundancy
doesn't hurt (perimeter overlaps null; only interior/rim pays) — the "two ball-handlers can't
coexist" myth doesn't survive.

## `mart_player_proj` — 20 rows, ORL/NOP rotation players · 2025-26
Rich per-player profile: `dpm/o_dpm/d_dpm`; full CTG shot **frequency + accuracy by zone**
(`freq_rim…freq_three`, `acc_rim/midrange/three`); `usage`, `ast_pct`, `ast_to_usg`,
`tov_pct`, `psa`; on/off (`net_on_off`, `rim_onoff_diff`, `rim_onoff_pctile`); **archetype
flags** `is_shooter` / `is_creator` / `is_rim_protector`.

**Informs:** player archetype classification; individual shot profiles; **role-coverage**
analysis (the biggest untested lead — does a lineup *missing a role* fail?); "who is/isn't a
shooter" narratives.

## `mart_roster` — 581 rows, one per player leaguewide · 2025-26
`player_name`, `team`, `position`, `dpm/o_dpm/d_dpm`, `mpg`.

**Informs:** roster win projections (A4 engine); team talent sums; minutes allocation;
trade/roster-move impact; leaguewide DPM leaderboards.

---

## Non-mart loaders (analytically useful, via `notebooks/_lab.py`)

- **`load_5man_features_2024()`** — same schema as `mart_lineup_features_league` but the
  **2024-25** held-out season (rebuilt from raw). Enables replication + pooled saturation.
- **`load_games_rim()`** — **per-game** rim protection (opponent + own at-rim scoring) for
  ORL/NOP, 2025-26. Enables clutch / fit-win-loss / per-game rim analysis.

## Notes for downstream analysis

- **Grain differs** across marts (team 30 / game 171 / lineup 600 league, 40 ORL-NOP /
  pair 556 / player 581 league, 20 ORL-NOP detail) — mind the join keys.
- **Biggest unexplored angle the data supports:** **role-coverage** — use
  `mart_player_proj`'s `is_shooter/is_creator/is_rim_protector` flags to test whether lineups
  *missing a role entirely* underperform (the "5 centers" failure mode the pairwise/overlap
  work couldn't reach).
