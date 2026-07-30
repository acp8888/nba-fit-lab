-- transform/21_mart_games_styled.sql
-- Mart: one row per ORL/NOP game, with the team's own game result plus the
-- opponent's season style profile attached (opp_* columns). Lets us ask "how do
-- our teams perform against fast / rim-heavy / elite-defense opponents?".
--
-- Join path resolves BBref opponent codes to CTG style rows:
--   stg_games.opponent (BBref abbr) -> stg_team_map.bbref_abbr
--   stg_team_map.full_name          -> mart_team_style.team_name

select
    g.team,
    g.season,
    g.game_date,
    g.game_num,
    g.is_away,
    g.opponent                                as opponent_abbr,
    tm.full_name                              as opponent_name,

    -- our team's result in this game
    g.result,
    g.team_pts,
    g.opp_pts,
    g.margin,
    g.o_rtg,
    g.d_rtg,
    g.net_rtg,
    g.pace,

    -- our shot mix / efficiency this game (for A3 process-adaptation analysis)
    g.three_pa_rate,
    g.off_efg_pct,

    -- rolling form: mean net rating over this + prior 9 games (window drill)
    avg(g.net_rtg) over (
        partition by g.team
        order by g.game_date, g.game_num
        rows between 9 preceding and current row
    )                                         as rolling_10_net_rtg,

    -- opponent's season identity (from mart_team_style)
    s.off_pts_poss                            as opp_off_pts_poss,
    s.def_pts_poss                            as opp_def_pts_poss,
    s.net_pts_poss                            as opp_net_pts_poss,
    s.off_rim_rate                            as opp_off_rim_rate,
    s.off_three_pa_rate                       as opp_off_three_pa_rate,
    s.off_transition_rate                     as opp_off_transition_rate,
    s.def_efg_pct                             as opp_def_efg_pct,
    s.def_tov_forced_pct                      as opp_def_tov_forced_pct,
    s.def_rim_rate_allowed                    as opp_def_rim_rate_allowed,
    s.def_three_pa_rate_allowed               as opp_def_three_pa_rate_allowed,
    s.pace                                    as opp_pace

from stg_games g
join stg_team_map tm    on g.opponent = tm.bbref_abbr
join mart_team_style s  on tm.full_name = s.team_name

-- ASSERTIONS (enforced by run.py):
-- every game is kept (inner joins must not drop rows) and fully resolved
-- ASSERT == 171: SELECT count(*) FROM mart_games_styled
-- ASSERT == 0: SELECT count(*) FROM mart_games_styled WHERE opponent_name IS NULL
-- ASSERT == 0: SELECT count(*) FROM mart_games_styled WHERE opp_net_pts_poss IS NULL
-- ASSERT == 0: SELECT count(*) FROM mart_games_styled WHERE rolling_10_net_rtg IS NULL
-- ASSERT == 0: SELECT count(*) FROM mart_games_styled WHERE team NOT IN ('ORL', 'NOP')
