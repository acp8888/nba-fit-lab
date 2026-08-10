-- transform/20_mart_team_style.sql
-- Mart: one row per NBA team-season describing offensive + defensive style.
-- Core style comes from stg_ctg_team (CTG, garbage-time filtered, all 30 teams);
-- sharp archetypes come from CTG's zone shooting frequencies, not raw per-100.
-- Augmented with two features CTG doesn't publish:
--   * pace  — from BBref team advanced (stg_team_advanced).
--   * size_wavg_height_in — minutes-weighted average roster height, from BBref
--     heights (stg_player_heights) weighted by DARKO minutes (stg_darko).
-- BBref and CTG agree on all 30 full team names, so the pace join is direct.

with heights as (
    -- BBref heights, both seasons (2024-25 = the 2025-07-08 pull, 2025-26 = 2026-07-08).
    select 2026 as season,
           lower(strip_accents("Player")) as pfold,
           cast(split_part("Ht",'-',1) as int)*12 + cast(split_part("Ht",'-',2) as int) as height_in
    from read_csv_auto('s3://nba-fit-lab/raw/bbref/2026-07-08/league_player_heights.csv')
    union all
    select 2025,
           lower(strip_accents("Player")),
           cast(split_part("Ht",'-',1) as int)*12 + cast(split_part("Ht",'-',2) as int)
    from read_csv_auto('s3://nba-fit-lab/raw/bbref/2025-07-08/league_player_heights.csv')
),
darko_mpg as (
    -- DARKO minutes per game, both seasons (full team name, for weighting height).
    select 2026 as season, lower(strip_accents("Player")) as pfold, "Team" as team_name, "MPG" as mpg
    from read_csv_auto('s3://nba-fit-lab/raw/darko/2026-07-08/darko-dpm-leaderboard.csv')
    union all
    select 2025, lower(strip_accents("Player")), "Team", "MPG"
    from read_csv_auto('s3://nba-fit-lab/raw/darko/2025-07-08/darko-dpm-leaderboard.csv')
),
team_size as (
    -- minutes-weighted average roster height per team-season (weights = DARKO MPG).
    select d.season, d.team_name,
           sum(h.height_in * d.mpg) / sum(d.mpg)               as size_wavg_height_in
    from darko_mpg d
    join heights h on h.pfold = d.pfold and h.season = d.season
    group by d.season, d.team_name
)

select
    s.team_name,
    s.season,

    -- tempo + size (BBref-sourced augmentations)
    ta.pace,
    round(ts.size_wavg_height_in, 2)                   as size_wavg_height_in,

    -- efficiency anchors (points per 100 possessions)
    off_pts_poss,
    def_pts_poss,
    off_pts_poss - def_pts_poss                        as net_pts_poss,

    -- offensive identity: four factors
    off_efg_pct,
    off_tov_pct,
    off_orb_pct,
    off_ft_rate,

    -- offensive shot diet (share of FGA by zone; sums to ~100)
    off_freq_rim                                        as off_rim_rate,
    off_freq_short_mid                                  as off_short_mid_rate,
    off_freq_long_mid                                   as off_long_mid_rate,
    off_freq_corner_three                               as off_corner_three_rate,
    off_freq_non_corner_three                           as off_non_corner_three_rate,
    off_freq_corner_three + off_freq_non_corner_three   as off_three_pa_rate,

    -- defensive identity: four factors + what you concede at the rim
    def_efg_pct,
    def_tov_pct                                         as def_tov_forced_pct,
    def_orb_pct                                         as def_orb_allowed_pct,
    def_ft_rate,
    def_freq_rim                                        as def_rim_rate_allowed,
    def_freq_corner_three + def_freq_non_corner_three   as def_three_pa_rate_allowed,

    -- tempo/context: transition vs halfcourt (frequency + efficiency)
    off_trans_freq                                      as off_transition_rate,
    off_trans_pts_per_play                              as off_transition_ppp,
    off_hc_pts_per_play                                 as off_halfcourt_ppp,
    def_trans_freq                                      as def_transition_rate_allowed,
    def_trans_pts_per_play                              as def_transition_ppp_allowed,
    def_hc_pts_per_play                                 as def_halfcourt_ppp_allowed

from stg_ctg_team s
left join stg_team_advanced ta on ta.team_name = s.team_name and ta.season = s.season
left join team_size ts on ts.team_name = s.team_name and ts.season = s.season

-- ASSERTIONS (enforced by run.py):
-- ASSERT == 60: SELECT count(*) FROM mart_team_style
-- ASSERT == 2: SELECT count(DISTINCT season) FROM mart_team_style
-- ASSERT == 30: SELECT count(*) FROM mart_team_style WHERE season = 2025
-- ASSERT == 0: SELECT count(*) FROM mart_team_style WHERE team_name IS NULL
-- ASSERT == 0: SELECT count(*) FROM mart_team_style WHERE net_pts_poss IS NULL
-- pace + size resolved for every team-season (join completeness across BOTH seasons)
-- ASSERT == 0: SELECT count(*) FROM mart_team_style WHERE pace IS NULL
-- ASSERT == 0: SELECT count(*) FROM mart_team_style WHERE size_wavg_height_in IS NULL
-- ASSERT == 0: SELECT count(*) FROM mart_team_style WHERE pace NOT BETWEEN 90 AND 110
-- weighted roster height in a sane band (~6'3"-6'11")
-- ASSERT == 0: SELECT count(*) FROM mart_team_style WHERE size_wavg_height_in NOT BETWEEN 75 AND 83
-- ASSERT == 0: SELECT count(*) FROM mart_team_style WHERE off_three_pa_rate NOT BETWEEN 0 AND 100
-- offensive zone frequencies should partition all FGA (allow rounding slack)
-- ASSERT == 0: SELECT count(*) FROM mart_team_style WHERE (off_rim_rate + off_short_mid_rate + off_long_mid_rate + off_corner_three_rate + off_non_corner_three_rate) NOT BETWEEN 98 AND 102
-- transition rates must be numeric percentages (guards against un-cast "%" strings)
-- ASSERT == 0: SELECT count(*) FROM mart_team_style WHERE off_transition_rate NOT BETWEEN 0 AND 100
-- ASSERT == 0: SELECT count(*) FROM mart_team_style WHERE def_transition_rate_allowed NOT BETWEEN 0 AND 100
