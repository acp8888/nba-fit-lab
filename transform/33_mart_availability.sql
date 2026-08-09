-- transform/33_mart_availability.sql
-- Mart: leaguewide player AVAILABILITY, both seasons (2024-25 = season 2025, 2025-26 = 2026).
-- One row per (season, team, player): games played, games missed vs an 82-game season, total
-- and per-game minutes, and DPM — the raw material for the "availability tax" (§8) and lineup
-- continuity. Built because the projection backtest's worst misses (PHI '25, NOP '25) are
-- availability collapses, not talent-model errors: talent predicts the roster a team COULD ice,
-- availability governs the roster it actually iced.
--
-- Source: BBref Advanced G + MP (per team-stint; a mid-season trade splits a player into two
-- rows, so G is games-for-THIS-team, not league games — a deliberate choice so team continuity
-- is measured, with the caveat that a low G can mean "arrived late" rather than "hurt"). DARKO
-- supplies DPM. Both seasons are completed 82-game regular seasons, so games_missed = 82 - gp.
-- Downstream computes the tax (e.g. greatest(dpm,0) * games_missed) — kept out of the mart so
-- the weighting scheme stays a notebook-level, documented choice.

with tmap(full_name, bbref) as (values
  ('Atlanta Hawks','ATL'),('Boston Celtics','BOS'),('Brooklyn Nets','BRK'),('Charlotte Hornets','CHO'),
  ('Chicago Bulls','CHI'),('Cleveland Cavaliers','CLE'),('Dallas Mavericks','DAL'),('Denver Nuggets','DEN'),
  ('Detroit Pistons','DET'),('Golden State Warriors','GSW'),('Houston Rockets','HOU'),('Indiana Pacers','IND'),
  ('Los Angeles Clippers','LAC'),('Los Angeles Lakers','LAL'),('Memphis Grizzlies','MEM'),('Miami Heat','MIA'),
  ('Milwaukee Bucks','MIL'),('Minnesota Timberwolves','MIN'),('New Orleans Pelicans','NOP'),('New York Knicks','NYK'),
  ('Oklahoma City Thunder','OKC'),('Orlando Magic','ORL'),('Philadelphia 76ers','PHI'),('Phoenix Suns','PHO'),
  ('Portland Trail Blazers','POR'),('Sacramento Kings','SAC'),('San Antonio Spurs','SAS'),('Toronto Raptors','TOR'),
  ('Utah Jazz','UTA'),('Washington Wizards','WAS')),

adv as (
  select 2025 as season, "Team" as team, "Player" as player_name,
         regexp_replace(lower(strip_accents("Player")), '\s+(jr\.?|sr\.?|ii|iii|iv)$', '') as fold,
         cast("G" as int) as gp, cast("MP" as int) as mp
  from read_csv('s3://nba-fit-lab/raw/bbref/2025-07-08/league_player_advanced.csv', skip=4)
  where "Team" not like '%TM' and cast("MP" as int) >= 100
  union all
  select 2026, "Team", "Player",
         regexp_replace(lower(strip_accents("Player")), '\s+(jr\.?|sr\.?|ii|iii|iv)$', ''),
         cast("G" as int), cast("MP" as int)
  from read_csv('s3://nba-fit-lab/raw/bbref/2026-07-08/league_player_advanced.csv', skip=4)
  where "Team" not like '%TM' and cast("MP" as int) >= 100
),
dk as (
  -- DARKO DPM is a player-level talent estimate; join on name+season only (not team) so a
  -- mid-season trade — which DARKO lists at the final team but BBref splits per stint — still
  -- resolves for both stints. One DARKO row per player-season, so (season, fold) is unique.
  select 2025 as season, regexp_replace(lower(strip_accents(dd."Player")), '\s+(jr\.?|sr\.?|ii|iii|iv)$', '') as fold,
         cast(regexp_replace(dd."DPM", '^\+', '') as double) as dpm
  from read_csv_auto('s3://nba-fit-lab/raw/darko/2025-07-08/darko-dpm-leaderboard.csv') dd
  union all
  select 2026, regexp_replace(lower(strip_accents(dd."Player")), '\s+(jr\.?|sr\.?|ii|iii|iv)$', ''),
         cast(regexp_replace(dd."DPM", '^\+', '') as double)
  from read_csv_auto('s3://nba-fit-lab/raw/darko/2026-07-08/darko-dpm-leaderboard.csv') dd
)

select
  a.team,
  a.player_name,
  a.gp,
  82                                     as team_games,
  greatest(82 - a.gp, 0)                 as games_missed,
  round(100.0 * a.gp / 82, 0)            as pct_games_avail,
  a.mp,
  round(a.mp / nullif(a.gp, 0), 1)       as mpg,
  dk.dpm,
  (a.mp >= 800)                          as is_rotation,
  a.season
from adv a
left join dk on dk.season = a.season and dk.fold = a.fold

-- ASSERTIONS (enforced by run.py):
-- ASSERT == 2: SELECT count(DISTINCT season) FROM mart_availability
-- ASSERT == 30: SELECT count(DISTINCT team) FROM mart_availability WHERE season = 2026
-- games played in a legal band
-- ASSERT == 0: SELECT count(*) FROM mart_availability WHERE gp NOT BETWEEN 1 AND 82
-- availability share in [0,100]
-- ASSERT == 0: SELECT count(*) FROM mart_availability WHERE pct_games_avail NOT BETWEEN 0 AND 100
-- games_missed reconciles with gp
-- ASSERT == 0: SELECT count(*) FROM mart_availability WHERE games_missed != 82 - gp
-- the availability story: Zion played far fewer games than Paolo in 2024-25 (the collapse season)
-- ASSERT == 1: SELECT count(*) FROM mart_availability WHERE season=2025 AND team='NOP' AND player_name='Zion Williamson' AND gp < 40
-- DPM resolves for rotation players (allow a handful of name-join gaps)
-- ASSERT < 15: SELECT count(*) FROM mart_availability WHERE is_rotation AND dpm IS NULL
