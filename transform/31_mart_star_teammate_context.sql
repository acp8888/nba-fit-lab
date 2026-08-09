-- transform/31_mart_star_teammate_context.sql
-- Mart: REALIZED star-teammate exposure, both seasons (2024-25 = season 2025, 2025-26 = 2026).
-- One row per (season, team, star, teammate): how many minutes the star ACTUALLY shared the
-- floor with each teammate, what share of the star's on-court minutes that was, and the
-- teammate's fit traits. This is "what environment did Paolo/Zion actually experience" — the
-- distinction §C of the brief calls REALIZED DEPLOYMENT, as opposed to roster construction or
-- roster architecture. Shared minutes come from BBref 2-man lineups; the star's on-court
-- minutes from BBref on/off; teammate traits from mart_player_league (an in-session table, so
-- traits are computed once, not re-derived here).
--
-- Season sources differ: 2024-25 pairs+on/off are LEAGUEWIDE files (filtered to ORL/NOP);
-- 2025-26 pairs+on/off are the team-specific orl_/nop_ files. Names arrive as "F. Last" and
-- are normalized to the same accent/suffix-stripped "f. last" key used across the pipeline.
--
-- CAVEATS: BBref exports only meaningful pairs, so a star's lowest-minute teammates may be
-- absent (their exposure is near-zero anyway). Teammates below the mart_player_league rotation
-- cut (MP<800) or unmatched get NULL traits (kept as rows; downstream weights by shared_min,
-- so they contribute ~nothing). pct_star_min_shared can exceed nothing sane only if minutes
-- mis-join — asserted below.

with stars(star, star_flast, star_fold, team) as (values
  -- star_flast matches the 2-man lineups ("F. Last"); star_fold matches on/off (full name)
  ('Paolo Banchero','p. banchero','paolo banchero','ORL'),
  ('Zion Williamson','z. williamson','zion williamson','NOP')
),
pairs as (
  -- 2024-25 leaguewide 2-man lineups, filtered to ORL/NOP
  select 2025 as season, "Team" as team, "Lineup" as lineup,
         cast(split_part("MP", ':', 1) as double) + cast(split_part("MP", ':', 2) as double)/60.0 as mp
  from read_csv_auto('s3://nba-fit-lab/raw/bbref/2025-07-08/league_lineups_2man.csv')
  where "Team" in ('ORL','NOP')
  union all
  select 2026, 'ORL', "Lineup",
         cast(split_part("MP", ':', 1) as double) + cast(split_part("MP", ':', 2) as double)/60.0
  from read_csv_auto('s3://nba-fit-lab/raw/bbref/2026-07-08/orl_lineups_2man.csv')
  union all
  select 2026, 'NOP', "Lineup",
         cast(split_part("MP", ':', 1) as double) + cast(split_part("MP", ':', 2) as double)/60.0
  from read_csv_auto('s3://nba-fit-lab/raw/bbref/2026-07-08/nop_lineups_2man.csv')
),
split as (
  select season, team, mp,
    regexp_replace(lower(strip_accents(trim(string_split(lineup, ' | ')[1]))), '\s+(jr\.?|sr\.?|ii|iii|iv)$', '') as p1,
    regexp_replace(lower(strip_accents(trim(string_split(lineup, ' | ')[2]))), '\s+(jr\.?|sr\.?|ii|iii|iv)$', '') as p2
  from pairs
),
star_pairs as (
  select s.season, s.team, st.star, st.star_fold,
         case when s.p1 = st.star_flast then s.p2 else s.p1 end as teammate,
         s.mp as shared_min
  from split s
  join stars st on st.team = s.team and st.star_flast in (s.p1, s.p2)
),
star_min as (
  select 2025 as season, "Team" as team,
         regexp_replace(lower(strip_accents("Player")), '\s+(jr\.?|sr\.?|ii|iii|iv)$', '') as pk,
         cast("MP" as double) as star_oncourt_min
  from read_csv_auto('s3://nba-fit-lab/raw/bbref/2025-07-08/league_onoff.csv')
  where "Split" = 'On Court' and "Team" in ('ORL','NOP')
  union all
  select 2026, 'ORL', regexp_replace(lower(strip_accents("Player")), '\s+(jr\.?|sr\.?|ii|iii|iv)$', ''), cast("MP" as double)
  from read_csv_auto('s3://nba-fit-lab/raw/bbref/2026-07-08/orl_onoff.csv') where "Split" = 'On Court'
  union all
  select 2026, 'NOP', regexp_replace(lower(strip_accents("Player")), '\s+(jr\.?|sr\.?|ii|iii|iv)$', ''), cast("MP" as double)
  from read_csv_auto('s3://nba-fit-lab/raw/bbref/2026-07-08/nop_onoff.csv') where "Split" = 'On Court'
),
tm as (
  -- teammate traits from the already-built mart (in-session table); key on "f. last"
  select season, team,
    regexp_replace(lower(strip_accents(
      left(player_name, 1) || '. ' || array_to_string(list_slice(string_split(player_name, ' '), 2, 100), ' ')
    )), '\s+(jr\.?|sr\.?|ii|iii|iv)$', '') as flast,
    player_name, dpm, usg, csg_pctl, tpar_pctl, rim_freq_pctl, height_in,
    is_shooter, is_creator, is_rim_protector
  from mart_player_league
)

select
  sp.team,
  sp.star,
  sp.teammate,
  tm.player_name                                             as teammate_name,
  round(sp.shared_min)                                       as shared_min,
  round(sm.star_oncourt_min)                                 as star_oncourt_min,
  round(100 * sp.shared_min / sm.star_oncourt_min, 1)        as pct_star_min_shared,
  tm.dpm                                                     as tm_dpm,
  round(tm.usg, 1)                                           as tm_usg,
  tm.csg_pctl                                                as tm_csg_pctl,
  tm.tpar_pctl                                               as tm_tpar_pctl,
  tm.rim_freq_pctl                                           as tm_rim_freq_pctl,
  tm.height_in                                               as tm_height_in,
  tm.is_shooter                                              as tm_is_shooter,
  tm.is_creator                                              as tm_is_creator,
  tm.is_rim_protector                                        as tm_is_rim_protector,
  sp.season
from star_pairs sp
join star_min sm on sm.season = sp.season and sm.team = sp.team and sm.pk = sp.star_fold
left join tm on tm.season = sp.season and tm.team = sp.team and tm.flast = sp.teammate

-- ASSERTIONS (enforced by run.py):
-- ASSERT == 2: SELECT count(DISTINCT season) FROM mart_star_teammate_context
-- ASSERT == 2: SELECT count(DISTINCT star) FROM mart_star_teammate_context
-- both stars present in both seasons (4 star-seasons)
-- ASSERT == 4: SELECT count(DISTINCT (season, star)) FROM mart_star_teammate_context
-- no self-pairs (the star's own flast never appears as a teammate)
-- ASSERT == 0: SELECT count(*) FROM mart_star_teammate_context WHERE teammate IN ('p. banchero','z. williamson')
-- shared minutes never exceed the star's own on-court minutes (guards the min join)
-- ASSERT == 0: SELECT count(*) FROM mart_star_teammate_context WHERE shared_min > star_oncourt_min + 1
-- exposure share in a sane band
-- ASSERT == 0: SELECT count(*) FROM mart_star_teammate_context WHERE pct_star_min_shared NOT BETWEEN 0 AND 100
-- star on-court minutes always resolved (inner join to on/off)
-- ASSERT == 0: SELECT count(*) FROM mart_star_teammate_context WHERE star_oncourt_min IS NULL
-- teammate traits resolve for the high-exposure teammates (rotation players); allow a few gaps
-- ASSERT < 4: SELECT count(*) FROM mart_star_teammate_context WHERE pct_star_min_shared >= 25 AND tm_dpm IS NULL
