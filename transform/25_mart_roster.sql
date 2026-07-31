-- transform/25_mart_roster.sql
-- Mart: leaguewide roster projection inputs — one row per player with DARKO
-- impact (DPM) and minutes (MPG), for the A4 win projection. The FULL roster is
-- required: projecting from just the top-10 over-rates bad teams (their deep
-- bench, which drags the season, is exactly what gets dropped). DARKO lists one
-- row per player (current team), so no per-stint duplication.

select
    d.player_name,
    tm.bbref_abbr                    as team,
    d.team                           as team_name,
    d.position,
    d.dpm,
    d.o_dpm,
    d.d_dpm,
    d.mpg,
    2026                             as season
from stg_darko d
join stg_team_map tm on d.team = tm.full_name
where d.mpg > 0

-- ASSERTIONS (enforced by run.py):
-- ASSERT > 400: SELECT count(*) FROM mart_roster
-- ASSERT == 30: SELECT count(DISTINCT team) FROM mart_roster
-- ASSERT == 0: SELECT count(*) FROM mart_roster WHERE dpm IS NULL
-- ASSERT == 0: SELECT count(*) FROM mart_roster WHERE mpg <= 0
