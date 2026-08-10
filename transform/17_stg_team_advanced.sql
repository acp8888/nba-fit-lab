-- transform/17_stg_team_advanced.sql
-- Staging: BBref league-wide team Advanced stats (all 30 teams). Source of team
-- PACE (the one column CTG doesn't publish).
--
-- BBref's "Get table as CSV" export is messy: a citation line + blank lines, then
-- a group-header row, then the real header on line 6, then data. Team names carry
-- a trailing '*' (playoff teams) and there is a 'League Average' summary row.
-- We read it positionally (header=false, skip=6) and take only what we need.
-- Column positions in the real header:  01=Team  13=Pace.

-- Both seasons share the same positional layout (skip=6, col01=team*, col13=pace); the
-- 2024-25 file is a separate pull (bbref/2026-08-07). Season-tagged and unioned so mart_team_style
-- can attach pace to both partitions.
select
    regexp_replace(column01, '\*$', '')        as team_name,
    cast(column13 as double)                    as pace,
    2026                                        as season
from read_csv(
    's3://nba-fit-lab/raw/bbref/2026-07-08/league_team_advanced.csv',
    header = false, skip = 6, all_varchar = true
)
where column01 is not null and column01 not in ('', 'League Average')

union all

select
    regexp_replace(column01, '\*$', '')        as team_name,
    cast(column13 as double)                    as pace,
    2025                                        as season
from read_csv(
    's3://nba-fit-lab/raw/bbref/2026-08-07/league_team_advanced_2024-25.csv',
    header = false, skip = 6, all_varchar = true
)
where column01 is not null and column01 not in ('', 'League Average')

-- ASSERTIONS (enforced by run.py):
-- ASSERT == 60: SELECT count(*) FROM stg_team_advanced
-- ASSERT == 2: SELECT count(DISTINCT season) FROM stg_team_advanced
-- ASSERT == 0: SELECT count(*) FROM stg_team_advanced WHERE team_name IS NULL
-- pace in a sane band both seasons (guards the positional parse)
-- ASSERT == 0: SELECT count(*) FROM stg_team_advanced WHERE pace NOT BETWEEN 90 AND 110
-- NBA team pace sits ~94-104 possessions/48; guards the positional parse
-- ASSERT == 0: SELECT count(*) FROM stg_team_advanced WHERE pace NOT BETWEEN 90 AND 110
