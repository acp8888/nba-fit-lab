-- transform/24_mart_lineup_features_league.sql
-- Mart: leaguewide lineup analysis table (all 30 teams' ~top-20 BBref 5-man
-- lineups, 600 rows) for the A2 scarcity regression. This is the POWER version
-- of mart_lineup_features (which is ORL/NOP-only with richer CTG features); here
-- every feature comes from BBref/DARKO so it's leaguewide and consistent.
--
-- Per lineup: the outcome (net_pts_per100), a talent baseline (sum of the five
-- players' DARKO DPM), and CONTINUOUS fit features. "Fit" is studied as the
-- residual net_pts_per100 - talent_sum_dpm (performance beyond talent).
--
-- Player attributes are joined by an accent-folded full-name key + team (DARKO,
-- heights, advanced all use full names); lineup slots are matched with the
-- same "F. Last" key used in mart_lineup_features. ~99.8% of slots resolve.
--
-- AMBIGUITY: a few teams have two players sharing "F. Last" (OKC: Jalen AND
-- Jaylin Williams; GSW: Stephen AND Seth Curry). "F. Last" can't tell them
-- apart, so we resolve each such key to the higher-minutes player (the star,
-- correct nearly always); a handful of bench-twin lineups are mis-attributed.
-- Each source lineup keeps its own row (lineup_id) so distinct lineups that
-- collapse to the same ambiguous key are not merged.
--
-- Spacing comes in two forms: spacing_mean/min from 3PA rate (willingness only,
-- BBref/public), and spacing_gravity_mean/min = willingness x accuracy from CTG
-- (stg_ctg_gravity_league). The gravity version is the fair test of spacing.

with adv as (
    select
        *,
        regexp_replace(lower(strip_accents(player_name)), '\s+(jr\.?|sr\.?|ii|iii|iv)$', '') as fold,
        regexp_replace(lower(strip_accents(
            left(player_name, 1) || '. ' ||
            array_to_string(list_slice(string_split(player_name, ' '), 2, 100), ' ')
        )), '\s+(jr\.?|sr\.?|ii|iii|iv)$', '') as flast
    from stg_player_advanced
),
dk as (
    select *, regexp_replace(lower(strip_accents(player_name)), '\s+(jr\.?|sr\.?|ii|iii|iv)$', '') as fold
    from stg_darko
),
ht as (
    select *, regexp_replace(lower(strip_accents(player_name)), '\s+(jr\.?|sr\.?|ii|iii|iv)$', '') as fold
    from stg_player_heights
),

attr as (
    -- one row per (team, F.Last key); on collision keep the higher-minutes player
    select
        adv.team_bbref                            as team,
        adv.flast                                 as k,
        dk.dpm,
        adv.usg,
        adv.ast_pct,
        adv.blk_pct,
        adv.three_pa_rate                         as par,
        ht.height_in,
        g.gravity
    from adv
    join stg_team_map tm on adv.team_bbref = tm.bbref_abbr
    left join dk on dk.fold = adv.fold and dk.team = tm.full_name
    left join ht on ht.fold = adv.fold and ht.team_bbref = adv.team_bbref
    left join stg_ctg_gravity_league g on regexp_replace(lower(strip_accents(g.player_name)), '\s+(jr\.?|sr\.?|ii|iii|iv)$', '') = adv.fold
    qualify row_number() over (partition by adv.team_bbref, adv.flast order by adv.mp desc) = 1
),

lu as (
    select
        row_number() over () as lineup_id,
        lineup_key, team, minutes, net_pts_per100,
        unnest([
            regexp_replace(lower(strip_accents(player_1)), '\s+(jr\.?|sr\.?|ii|iii|iv)$', ''),
            regexp_replace(lower(strip_accents(player_2)), '\s+(jr\.?|sr\.?|ii|iii|iv)$', ''),
            regexp_replace(lower(strip_accents(player_3)), '\s+(jr\.?|sr\.?|ii|iii|iv)$', ''),
            regexp_replace(lower(strip_accents(player_4)), '\s+(jr\.?|sr\.?|ii|iii|iv)$', ''),
            regexp_replace(lower(strip_accents(player_5)), '\s+(jr\.?|sr\.?|ii|iii|iv)$', '')
        ]) as k
    from stg_lineups_league
)

select
    any_value(lu.lineup_key)                      as lineup_key,
    any_value(lu.team)                            as team,
    2026                                          as season,
    any_value(lu.minutes)                         as minutes,
    any_value(lu.net_pts_per100)                  as net_pts_per100,

    count(a.k)                                    as n_covered,
    sum(a.dpm)                                    as talent_sum_dpm,
    any_value(lu.net_pts_per100) - sum(a.dpm)     as fit_residual,

    -- continuous fit features (over covered players)
    avg(a.par)                                    as spacing_mean,
    min(a.par)                                    as spacing_min,
    -- spacing as willingness x accuracy (3pt gravity); the fair-shot version
    avg(a.gravity)                                as spacing_gravity_mean,
    min(a.gravity)                                as spacing_gravity_min,
    max(a.blk_pct)                                as rim_max_blk,
    max(a.height_in)                              as tallest_in,
    max(a.usg)                                    as usg_max,
    stddev_pop(a.usg)                             as usg_spread,
    max(a.ast_pct)                                as ast_max

from lu
left join attr a on a.team = lu.team and a.k = lu.k
group by lu.lineup_id

-- ASSERTIONS (enforced by run.py):
-- ASSERT == 600: SELECT count(*) FROM mart_lineup_features_league
-- ASSERT == 30: SELECT count(DISTINCT team) FROM mart_lineup_features_league
-- ASSERT == 0: SELECT count(*) FROM mart_lineup_features_league WHERE n_covered NOT BETWEEN 0 AND 5
-- name matching resolves nearly every lineup fully (coverage sanity)
-- ASSERT > 500: SELECT count(*) FROM mart_lineup_features_league WHERE n_covered = 5
-- outcome + talent present for analysis
-- ASSERT == 0: SELECT count(*) FROM mart_lineup_features_league WHERE net_pts_per100 IS NULL
-- ASSERT == 0: SELECT count(*) FROM mart_lineup_features_league WHERE fit_residual IS NULL
-- BLK% in a sane band (guards the join/parse)
-- ASSERT == 0: SELECT count(*) FROM mart_lineup_features_league WHERE rim_max_blk NOT BETWEEN 0 AND 20
