-- transform/04_stg_ctg_gravity_league.sql
-- Staging: league-wide player 3-point "gravity" = willingness x ability, from
-- CTG's leaguewide shooting FREQUENCY and ACCURACY exports (both "All Three").
--   gravity = (3PA frequency / 100) * 3P accuracy    (both are % shares)
-- Non-shooters have NaN accuracy -> gravity 0. Traded players appear as multiple
-- per-team stints; we keep the max-minutes stint (one row per player).
--
-- This gives spacing a fair test in mart_lineup_features_league: not just 3PA
-- rate (willingness) but whether the shots go in (ability). NOTE: CTG-derived,
-- so any mart that uses it inherits the CTG licensing constraint (keep private).

select player_name, gravity, min
from (
    select
        fr."Player"                                                   as player_name,
        (cast(replace(fr."All Three", '%', '') as double) / 100.0)
            * coalesce(cast(replace(ac."All Three", '%', '') as double), 0) as gravity,
        fr."MIN"                                                      as min,
        row_number() over (
            partition by lower(strip_accents(fr."Player"))
            order by fr."MIN" desc
        ) as rn
    from read_csv_auto('s3://nba-fit-lab/raw/ctg/2026-07-08/league_player_shooting_frequency.csv') fr
    join read_csv_auto('s3://nba-fit-lab/raw/ctg/2026-07-08/league_player_shooting_accuracy.csv') ac
        on fr."Player" = ac."Player"
)
where rn = 1

-- ASSERTIONS (enforced by run.py):
-- ASSERT > 400: SELECT count(*) FROM stg_ctg_gravity_league
-- one row per player (dedup worked)
-- ASSERT == 0: SELECT count(*) - count(DISTINCT lower(strip_accents(player_name))) FROM stg_ctg_gravity_league
-- ASSERT == 0: SELECT count(*) FROM stg_ctg_gravity_league WHERE gravity IS NULL
-- ASSERT == 0: SELECT count(*) FROM stg_ctg_gravity_league WHERE gravity NOT BETWEEN 0 AND 60
