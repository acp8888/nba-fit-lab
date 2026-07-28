-- transform/10_stg_lineups.sql
-- Staging: ORL + NOP 5-man lineups, 2026 season

with orl_source as (
    select
        *,
        filename as source_file,
        'ORL'    as team,
        2026     as season
    from read_csv_auto(
        's3://nba-fit-lab/raw/bbref/2026-07-08/orl_lineups_5man.csv',
        filename = true
    )
),

nop_source as (
    select
        *,
        filename as source_file,
        'NOP'    as team,
        2026     as season
    from read_csv_auto(
        's3://nba-fit-lab/raw/bbref/2026-07-08/nop_lineups_5man.csv',
        filename = true
    )
),

source as (
    select * from orl_source
    union all
    select * from nop_source
),

split as (
    select
        *,
        string_split("Lineup", ' | ')             as lineup_arr,
        list_sort(string_split("Lineup", ' | '))   as lineup_arr_sorted
    from source
)

select
    array_to_string(lineup_arr_sorted, '|')                     as lineup_key,
    lineup_arr[1]                                                as player_1,
    lineup_arr[2]                                                as player_2,
    lineup_arr[3]                                                as player_3,
    lineup_arr[4]                                                as player_4,
    lineup_arr[5]                                                as player_5,

    cast(split_part("MP", ':', 1) as double)
        + cast(split_part("MP", ':', 2) as double) / 60.0        as minutes,

    cast(regexp_replace("PTS",  '^\+', '') as double)            as pts,
    cast(regexp_replace("FG",   '^\+', '') as double)            as fg,
    cast(regexp_replace("FGA",  '^\+', '') as double)            as fga,
    cast(regexp_replace("3P",   '^\+', '') as double)            as three_p,
    cast(regexp_replace("3PA",  '^\+', '') as double)            as three_pa,
    cast(regexp_replace("3P%",  '^\+', '') as double)            as three_pct,
    cast(regexp_replace("eFG%", '^\+', '') as double)            as efg_pct,
    cast(regexp_replace("FT",   '^\+', '') as double)            as ft,
    cast(regexp_replace("FTA",  '^\+', '') as double)            as fta,
    cast(regexp_replace("FT%",  '^\+', '') as double)            as ft_pct,
    cast(regexp_replace("ORB",  '^\+', '') as double)            as orb,
    cast(regexp_replace("DRB",  '^\+', '') as double)            as drb,
    cast(regexp_replace("TRB",  '^\+', '') as double)            as trb,
    cast(regexp_replace("AST",  '^\+', '') as double)            as ast,
    cast(regexp_replace("STL",  '^\+', '') as double)            as stl,
    cast(regexp_replace("BLK",  '^\+', '') as double)            as blk,
    cast(regexp_replace("TOV",  '^\+', '') as double)            as tov,
    cast(regexp_replace("PF",   '^\+', '') as double)            as pf,

    team,
    season,
    source_file

from split

-- ASSERTIONS (enforced by run.py):
-- ASSERT == 0: SELECT count(*) FROM stg_lineups WHERE minutes <= 0
-- ASSERT == 0: SELECT count(*) FROM stg_lineups WHERE lineup_key IS NULL
-- ASSERT == 0: SELECT count(*) FROM stg_lineups WHERE team NOT IN ('ORL', 'NOP')