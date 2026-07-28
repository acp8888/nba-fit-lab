-- transform/20_mart_team_style.sql
-- Mart: one row per NBA team-season describing offensive + defensive style,
-- built entirely from stg_ctg_team (CTG, garbage-time filtered, all 30 teams).
-- This is the clustering contract — sharp archetypes come from CTG's zone
-- shooting frequencies, not raw per-100 rates.
--
-- DEFERRED (not in current data; needs new ingest before backfilling here):
--   * pace       — CTG exports per-possession efficiency but no tempo. Needs a
--                  BBref team-per-game (or CTG pace) export.
--   * size_proxy — needs a BBref roster/height export.
-- Add these columns when their sources are ingested; leaving them out keeps the
-- mart honest rather than shipping all-null columns.

select
    team_name,
    season,

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

from stg_ctg_team

-- ASSERTIONS (enforced by run.py):
-- ASSERT == 30: SELECT count(*) FROM mart_team_style
-- ASSERT == 0: SELECT count(*) FROM mart_team_style WHERE team_name IS NULL
-- ASSERT == 0: SELECT count(*) FROM mart_team_style WHERE net_pts_poss IS NULL
-- ASSERT == 0: SELECT count(*) FROM mart_team_style WHERE off_three_pa_rate NOT BETWEEN 0 AND 100
-- offensive zone frequencies should partition all FGA (allow rounding slack)
-- ASSERT == 0: SELECT count(*) FROM mart_team_style WHERE (off_rim_rate + off_short_mid_rate + off_long_mid_rate + off_corner_three_rate + off_non_corner_three_rate) NOT BETWEEN 98 AND 102
-- transition rates must be numeric percentages (guards against un-cast "%" strings)
-- ASSERT == 0: SELECT count(*) FROM mart_team_style WHERE off_transition_rate NOT BETWEEN 0 AND 100
-- ASSERT == 0: SELECT count(*) FROM mart_team_style WHERE def_transition_rate_allowed NOT BETWEEN 0 AND 100
