-- transform/12_stg_games.sql
-- Staging: ORL + NOP advanced game logs, 2026 season

with orl_source as (
    select *, filename as source_file, 'ORL' as team
    from read_csv_auto(
        's3://nba-fit-lab/raw/bbref/2026-07-08/orl_gamelog_advanced.csv',
        filename = true
    )
),

nop_source as (
    select *, filename as source_file, 'NOP' as team
    from read_csv_auto(
        's3://nba-fit-lab/raw/bbref/2026-07-08/nop_gamelog_advanced.csv',
        filename = true
    )

),

source as (
    select * from orl_source
    union all
    select * from nop_source
)

select
    team,
    "Date"                              as game_date,
    "Gtm"                               as game_num,
    case when "Away" = '@' then true
         else false end                 as is_away,
    "Opp"                               as opponent,
    "Rslt"                              as result,
    "Tm"                                as team_pts,
    "OppPts"                            as opp_pts,
    "Tm" - "OppPts"                     as margin,
    "ORtg"                              as o_rtg,
    "DRtg"                              as d_rtg,
    "ORtg" - "DRtg"                     as net_rtg,
    "Pace"                              as pace,
    "3PAr"                              as three_pa_rate,
    "TS%"                               as ts_pct,
    "Off_eFG%"                          as off_efg_pct,
    "Off_TOV%"                          as off_tov_pct,
    "Off_ORB%"                          as off_orb_pct,
    "Off_FT/FGA"                        as off_ft_rate,
    "Def_eFG%"                          as def_efg_pct,
    "Def_TOV%"                          as def_tov_pct,
    "Def_ORB%"                          as def_orb_pct,
    "Def_FT/FGA"                        as def_ft_rate,
    2026                                as season,
    source_file

from source
where "Rk" is not null
  and "Date" is not null

-- ASSERTIONS (enforced by run.py):
-- ASSERT == 0: SELECT count(*) FROM stg_games WHERE margin != team_pts - opp_pts
-- ASSERT == 0: SELECT count(*) FROM stg_games WHERE team NOT IN ('ORL', 'NOP')
-- ASSERT == 0: SELECT count(*) FROM stg_games WHERE game_date IS NULL
