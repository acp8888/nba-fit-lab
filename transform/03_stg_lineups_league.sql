-- transform/03_stg_lineups_league.sql
-- Staging: BBref 5-man lineups for all 30 teams (league_lineups_5man.csv, ~20 per
-- team). Same shape as stg_lineups (ORL/NOP) but leaguewide and keyed off the
-- file's Team column. net_pts_per100 is BBref's signed lineup value, validated
-- as a possession-true net rating per 100 (see mart_lineup_features).

with source as (
    select
        *,
        "Team"                                       as team,
        string_split("Lineup", ' | ')                as lineup_arr,
        list_sort(string_split("Lineup", ' | '))     as lineup_arr_sorted
    from read_csv_auto(
        's3://nba-fit-lab/raw/bbref/2026-07-08/league_lineups_5man.csv'
    )
)

select
    array_to_string(lineup_arr_sorted, '|')          as lineup_key,
    team,
    lineup_arr[1]                                     as player_1,
    lineup_arr[2]                                     as player_2,
    lineup_arr[3]                                     as player_3,
    lineup_arr[4]                                     as player_4,
    lineup_arr[5]                                     as player_5,

    cast(split_part("MP", ':', 1) as double)
        + cast(split_part("MP", ':', 2) as double) / 60.0   as minutes,
    cast(regexp_replace("PTS",  '^\+', '') as double)        as net_pts_per100,
    cast(regexp_replace("eFG%", '^\+', '') as double)        as efg_diff,
    2026                                              as season

from source

-- ASSERTIONS (enforced by run.py):
-- ASSERT == 600: SELECT count(*) FROM stg_lineups_league
-- ASSERT == 30: SELECT count(DISTINCT team) FROM stg_lineups_league
-- ASSERT == 0: SELECT count(*) FROM stg_lineups_league WHERE lineup_key IS NULL
-- ASSERT == 0: SELECT count(*) FROM stg_lineups_league WHERE minutes <= 0
-- five players parsed for every lineup
-- ASSERT == 0: SELECT count(*) FROM stg_lineups_league WHERE player_5 IS NULL
