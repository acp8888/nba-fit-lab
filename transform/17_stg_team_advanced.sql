-- transform/17_stg_team_advanced.sql
-- Staging: BBref league-wide team Advanced stats (all 30 teams). Source of team
-- PACE (the one column CTG doesn't publish).
--
-- BBref's "Get table as CSV" export is messy: a citation line + blank lines, then
-- a group-header row, then the real header on line 6, then data. Team names carry
-- a trailing '*' (playoff teams) and there is a 'League Average' summary row.
-- We read it positionally (header=false, skip=6) and take only what we need.
-- Column positions in the real header:  01=Team  13=Pace.

select
    regexp_replace(column01, '\*$', '')        as team_name,
    cast(column13 as double)                    as pace,
    2026                                        as season

from read_csv(
    's3://nba-fit-lab/raw/bbref/2026-07-08/league_team_advanced.csv',
    header = false, skip = 6, all_varchar = true
)
where column01 is not null
  and column01 not in ('', 'League Average')

-- ASSERTIONS (enforced by run.py):
-- ASSERT == 30: SELECT count(*) FROM stg_team_advanced
-- ASSERT == 0: SELECT count(*) FROM stg_team_advanced WHERE team_name IS NULL
-- NBA team pace sits ~94-104 possessions/48; guards the positional parse
-- ASSERT == 0: SELECT count(*) FROM stg_team_advanced WHERE pace NOT BETWEEN 90 AND 110
