select
    "Player"                                          as player_name,
    "Team"                                             as team,
    "Pos"                                              as position,

    cast(regexp_replace("DPM",  '^\+', '') as double)  as dpm,
    cast(regexp_replace("ODPM", '^\+', '') as double)  as o_dpm,
    cast(regexp_replace("DDPM", '^\+', '') as double)  as d_dpm,

    "MPG"                                              as mpg,

    date '2026-07-08'                                  as snapshot_date,
    filename                                           as source_file

from read_csv_auto(
    's3://nba-fit-lab/raw/darko/2026-07-08/darko-dpm-leaderboard.csv',
    filename = true
)

-- ASSERTIONS (enforced by run.py):
-- ASSERT > 0: SELECT count(*) FROM stg_darko
-- ASSERT == 0: SELECT count(*) FROM stg_darko WHERE player_name IS NULL
-- ASSERT == 0: SELECT count(*) FROM stg_darko WHERE dpm IS NULL