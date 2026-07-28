-- transform/15_stg_pbp_lineups.sql
-- Staging: PBPStats 5-man lineup data, ORL + NOP, 2026 season
-- ShortName is comma-separated last names — sorted to create a lineup key.
-- NOTE: name format differs from BBref (last-only vs "F. Last"). Cross-source
--       lineup joining requires a name map and happens in the mart, not here.

with orl_source as (
    select *, 'ORL' as team
    from read_csv_auto('s3://nba-fit-lab/raw/pbpstats/2026-07-08/orl_pbpstats_lineups_5man.csv')
),

nop_source as (
    select *, 'NOP' as team
    from read_csv_auto('s3://nba-fit-lab/raw/pbpstats/2026-07-08/nop_pbpstats_lineups_5man.csv')
),

source as (
    select * from orl_source
    union all
    select * from nop_source
)

select
    array_to_string(list_sort(string_split("ShortName", ', ')), '|') as lineup_key_pbp,
    "ShortName"                                                        as lineup_short_name,
    team,
    2026                                                               as season,
    "GamesPlayed"                                                      as games_played,
    "Minutes"                                                          as minutes,
    "PlusMinus"                                                        as plus_minus,
    "OffPoss"                                                          as off_poss,
    "Points"                                                           as points,
    "FG2M"                                                             as fg2m,
    "FG2A"                                                             as fg2a,
    "FG3M"                                                             as fg3m,
    "FG3A"                                                             as fg3a,
    "Fg3Pct"                                                           as fg3_pct,
    "FtPoints"                                                         as ft_points,
    "FG3APct"                                                          as fg3a_pct,
    "EfgPct"                                                           as efg_pct,
    "TsPct"                                                            as ts_pct,
    "ShotQualityAvg"                                                   as shot_quality_avg,
    "FG2APctBlocked"                                                   as fg2a_pct_blocked

from source
-- Drop lineups with no offensive possessions (garbage-time 1-2 game samples);
-- off_poss = 0 would divide-by-zero in downstream per-100 mart calcs.
where "OffPoss" > 0

-- ASSERTIONS (enforced by run.py):
-- ASSERT == 0: SELECT count(*) FROM stg_pbp_lineups WHERE team NOT IN ('ORL', 'NOP')
-- ASSERT == 0: SELECT count(*) FROM stg_pbp_lineups WHERE off_poss <= 0
-- ASSERT == 0: SELECT count(*) FROM stg_pbp_lineups WHERE lineup_key_pbp IS NULL
