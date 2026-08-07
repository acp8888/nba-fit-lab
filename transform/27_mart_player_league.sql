-- transform/27_mart_player_league.sql
-- Mart: leaguewide per-player archetype profile, BOTH seasons (2024-25 = season 2025,
-- 2025-26 = season 2026). One row per (season, team, player) rotation player (MP >= 800),
-- with raw traits, within-season LEAGUE PERCENTILES, and tunable archetype FLAGS.
-- Foundation for the star-archetype / inversion analysis (Post 1), the leaguewide
-- generalization (Analysis C), and role coverage (Post 3 / Analysis D).
--
-- Reads raw for BOTH seasons directly — a documented exception to "marts read staging":
-- the base staging is single-season (2025-26) and this is the only two-season player table.
-- Sources (all public / leaguewide): BBref advanced (USG%/3PAr/AST%/TS%/BLK%), NBA.com shot
-- types (catch-&-shoot gravity), DARKO (DPM), BBref heights.
--
-- FLAGS (tunable, percentile-based heuristics; is_rim_protector is a BLK%+size PROXY, since
-- CTG rim on/off is ORL/NOP-only):
--   is_ball_dominant_nonshooter — usg pctl>=80 AND 3PAr pctl<=40 AND C&S pctl<=40
--                                 (the Banchero/Williamson star archetype; drives Analysis C)
--   is_shooter        — C&S-gravity pctl >= 60 (a real floor-spacing threat)
--   is_creator        — usage >= 24 OR AST:Usg >= 1.15 (matches mart_player_proj)
--   is_rim_protector  — BLK% pctl >= 75 AND height >= 82in (leaguewide proxy)

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
  select season, team, player_name,
         regexp_replace(lower(strip_accents(player_name)), '\s+(jr\.?|sr\.?|ii|iii|iv)$', '') as fold,
         mp, usg, three_pa_rate, ast_pct, ts_pct, blk_pct
  from (
    select 2025 as season, "Team" as team, "Player" as player_name, cast("MP" as int) as mp,
           cast("USG%" as double) usg, cast("3PAr" as double) three_pa_rate,
           cast("AST%" as double) ast_pct, cast("TS%" as double) ts_pct, cast("BLK%" as double) blk_pct
    from read_csv('s3://nba-fit-lab/raw/bbref/2025-07-08/league_player_advanced.csv', skip=4)
    where "Team" not like '%TM' and cast("MP" as int) >= 800
    union all
    select 2026, "Team", "Player", cast("MP" as int),
           cast("USG%" as double), cast("3PAr" as double),
           cast("AST%" as double), cast("TS%" as double), cast("BLK%" as double)
    from read_csv('s3://nba-fit-lab/raw/bbref/2026-07-08/league_player_advanced.csv', skip=4)
    where "Team" not like '%TM' and cast("MP" as int) >= 800
  )
),
st as (
  select 2025 as season,
         regexp_replace(lower(strip_accents("Player")), '\s+(jr\.?|sr\.?|ii|iii|iv)$', '') as fold,
         case "Team" when 'BKN' then 'BRK' when 'CHA' then 'CHO' when 'PHX' then 'PHO' else "Team" end as team,
         coalesce(("CS_FG3A"::double/nullif("MIN",0)*36.0)*"CS_FG3_PCT"::double, 0) as cs_gravity
  from read_csv_auto('s3://nba-fit-lab/raw/nbastats/2025-07-08/league_player_shot_types.csv')
  union all
  select 2026,
         regexp_replace(lower(strip_accents("Player")), '\s+(jr\.?|sr\.?|ii|iii|iv)$', ''),
         case "Team" when 'BKN' then 'BRK' when 'CHA' then 'CHO' when 'PHX' then 'PHO' else "Team" end,
         coalesce(("CS_FG3A"::double/nullif("MIN",0)*36.0)*"CS_FG3_PCT"::double, 0)
  from read_csv_auto('s3://nba-fit-lab/raw/nbastats/2026-07-08/league_player_shot_types.csv')
),
dk as (
  select 2025 as season, regexp_replace(lower(strip_accents(dd."Player")), '\s+(jr\.?|sr\.?|ii|iii|iv)$', '') as fold,
         tm.bbref as team, cast(regexp_replace(dd."DPM", '^\+', '') as double) as dpm
  from read_csv_auto('s3://nba-fit-lab/raw/darko/2025-07-08/darko-dpm-leaderboard.csv') dd
  join tmap tm on dd."Team" = tm.full_name
  union all
  select 2026, regexp_replace(lower(strip_accents(dd."Player")), '\s+(jr\.?|sr\.?|ii|iii|iv)$', ''),
         tm.bbref, cast(regexp_replace(dd."DPM", '^\+', '') as double)
  from read_csv_auto('s3://nba-fit-lab/raw/darko/2026-07-08/darko-dpm-leaderboard.csv') dd
  join tmap tm on dd."Team" = tm.full_name
),
ht as (
  select 2025 as season, regexp_replace(lower(strip_accents("Player")), '\s+(jr\.?|sr\.?|ii|iii|iv)$', '') as fold,
         "Team" as team, cast(split_part("Ht",'-',1) as int)*12 + cast(split_part("Ht",'-',2) as int) as height_in
  from read_csv_auto('s3://nba-fit-lab/raw/bbref/2025-07-08/league_player_heights.csv')
  union all
  select 2026, regexp_replace(lower(strip_accents("Player")), '\s+(jr\.?|sr\.?|ii|iii|iv)$', ''),
         "Team", cast(split_part("Ht",'-',1) as int)*12 + cast(split_part("Ht",'-',2) as int)
  from read_csv_auto('s3://nba-fit-lab/raw/bbref/2026-07-08/league_player_heights.csv')
),
base as (
  select a.season, a.team, a.player_name, a.mp,
         a.usg, a.three_pa_rate, a.ast_pct, a.ts_pct, a.blk_pct,
         a.ast_pct / nullif(a.usg, 0) as ast_to_usg,
         coalesce(st.cs_gravity, 0) as cs_gravity,
         dk.dpm, ht.height_in
  from adv a
  left join st on st.season = a.season and st.fold = a.fold and st.team = a.team
  left join dk on dk.season = a.season and dk.fold = a.fold and dk.team = a.team
  left join ht on ht.season = a.season and ht.fold = a.fold and ht.team = a.team
),
pct as (
  select *,
    round(100 * percent_rank() over (partition by season order by usg))          as usg_pctl,
    round(100 * percent_rank() over (partition by season order by three_pa_rate)) as tpar_pctl,
    round(100 * percent_rank() over (partition by season order by cs_gravity))    as csg_pctl,
    round(100 * percent_rank() over (partition by season order by ast_pct))       as ast_pctl,
    round(100 * percent_rank() over (partition by season order by ts_pct))        as ts_pctl,
    round(100 * percent_rank() over (partition by season order by blk_pct))       as blk_pctl,
    round(100 * percent_rank() over (partition by season order by dpm))           as dpm_pctl
  from base
)
select
  team, player_name, mp,
  round(usg,1) usg, round(three_pa_rate,3) three_pa_rate, round(ast_pct,1) ast_pct,
  round(ts_pct,3) ts_pct, round(blk_pct,1) blk_pct, round(ast_to_usg,2) ast_to_usg,
  round(cs_gravity,2) cs_gravity, dpm, height_in,
  usg_pctl, tpar_pctl, csg_pctl, ast_pctl, ts_pctl, blk_pctl, dpm_pctl,
  (usg_pctl >= 80 and tpar_pctl <= 40 and csg_pctl <= 40)  as is_ball_dominant_nonshooter,
  (csg_pctl >= 60)                                         as is_shooter,
  (usg >= 24 or ast_to_usg >= 1.15)                        as is_creator,
  (blk_pctl >= 75 and height_in >= 82)                     as is_rim_protector,
  season
from pct

-- ASSERTIONS (enforced by run.py):
-- ASSERT == 2: SELECT count(DISTINCT season) FROM mart_player_league
-- ASSERT > 200: SELECT count(*) FROM mart_player_league WHERE season = 2025
-- ASSERT > 200: SELECT count(*) FROM mart_player_league WHERE season = 2026
-- percentiles are within [0,100]
-- ASSERT == 0: SELECT count(*) FROM mart_player_league WHERE usg_pctl NOT BETWEEN 0 AND 100
-- ASSERT == 0: SELECT count(*) FROM mart_player_league WHERE csg_pctl NOT BETWEEN 0 AND 100
-- sanity: the two stars are flagged ball-dominant non-shooters; the elite spacer is not
-- ASSERT == 1: SELECT count(*) FROM mart_player_league WHERE season=2026 AND player_name='Paolo Banchero' AND is_ball_dominant_nonshooter
-- ASSERT == 1: SELECT count(*) FROM mart_player_league WHERE season=2026 AND player_name='Zion Williamson' AND is_ball_dominant_nonshooter
-- ASSERT == 1: SELECT count(*) FROM mart_player_league WHERE season=2026 AND player_name='Trey Murphy III' AND is_shooter AND NOT is_ball_dominant_nonshooter
