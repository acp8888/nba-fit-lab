-- transform/23_mart_lineup_features.sql
-- Mart: one row per BBref 5-man lineup with engineered "fit" features.
-- This is the analytical contract for the fit thesis.
--
-- Per-player fit FLAGS live in mart_player_proj (is_shooter / is_creator /
-- is_rim_protector, with their definitions); this mart just aggregates them over
-- each lineup's covered players:
--   n_shooters        — count of covered players flagged is_shooter (floor
--                       spacing; sparse by design).
--   n_creators        — count flagged is_creator (self-creation or playmaking).
--   has_rim_protector — TRUE if any covered player is a rim-protecting Big.
--   spacing_score     — sum over covered players of a 3pt gravity proxy
--                       (freq_three/100 * acc_three): willingness x ability.
--   n_covered         — how many of the 5 slots resolved to a rostered player
--                       with CTG features (0-5). ~9 bench players lack CTG
--                       profiles, so some lineups are partially covered; all
--                       features are computed over covered players only.
--
-- OUTCOME columns: minutes (reliable) and net_pts_per100 = BBref's signed lineup
-- differential (stg_lineups.pts). BBref gives no possession count, so this is
-- BBref's on-court net-point differential, NOT a possession-normalized rating;
-- a rigorous net rating would come from PBPStats (stg_pbp_lineups) — future work.
--
-- NAME MATCH: BBref lineup names are "F. Last"; roster names are full. One
-- normalization works for both — first-initial + '. ' + rest, accent-folded,
-- lowercased, trailing Jr./Sr./II/III/IV stripped. Resolves all 20 rostered
-- players (fixes Murphy III, Carter Jr., Matkovic).

with roster as (
    select
        team,
        regexp_replace(lower(strip_accents(
            left(player_name, 1) || '. ' ||
            array_to_string(list_slice(string_split(player_name, ' '), 2, 100), ' ')
        )), '\s+(jr\.?|sr\.?|ii|iii|iv)$', '')            as k,
        (freq_three / 100.0) * acc_three                   as gravity,
        is_shooter::int                                    as is_shooter,
        is_creator::int                                    as is_creator,
        is_rim_protector::int                              as is_rim_protector
    from mart_player_proj
),

lu as (
    select
        *,
        regexp_replace(lower(strip_accents(player_1)), '\s+(jr\.?|sr\.?|ii|iii|iv)$', '') as k1,
        regexp_replace(lower(strip_accents(player_2)), '\s+(jr\.?|sr\.?|ii|iii|iv)$', '') as k2,
        regexp_replace(lower(strip_accents(player_3)), '\s+(jr\.?|sr\.?|ii|iii|iv)$', '') as k3,
        regexp_replace(lower(strip_accents(player_4)), '\s+(jr\.?|sr\.?|ii|iii|iv)$', '') as k4,
        regexp_replace(lower(strip_accents(player_5)), '\s+(jr\.?|sr\.?|ii|iii|iv)$', '') as k5
    from stg_lineups
)

select
    lu.lineup_key,
    lu.team,
    lu.season,
    lu.minutes,
    lu.pts                                                as net_pts_per100,
    lu.player_1, lu.player_2, lu.player_3, lu.player_4, lu.player_5,

    -- coverage: slots resolved to a rostered player with CTG features
    (r1.k is not null)::int + (r2.k is not null)::int + (r3.k is not null)::int
        + (r4.k is not null)::int + (r5.k is not null)::int               as n_covered,

    coalesce(r1.is_shooter, 0) + coalesce(r2.is_shooter, 0) + coalesce(r3.is_shooter, 0)
        + coalesce(r4.is_shooter, 0) + coalesce(r5.is_shooter, 0)         as n_shooters,

    coalesce(r1.is_creator, 0) + coalesce(r2.is_creator, 0) + coalesce(r3.is_creator, 0)
        + coalesce(r4.is_creator, 0) + coalesce(r5.is_creator, 0)         as n_creators,

    (coalesce(r1.is_rim_protector, 0) + coalesce(r2.is_rim_protector, 0)
        + coalesce(r3.is_rim_protector, 0) + coalesce(r4.is_rim_protector, 0)
        + coalesce(r5.is_rim_protector, 0)) > 0                           as has_rim_protector,

    -- spacing: sum of covered players' 3pt gravity proxy
    round(coalesce(r1.gravity, 0) + coalesce(r2.gravity, 0) + coalesce(r3.gravity, 0)
        + coalesce(r4.gravity, 0) + coalesce(r5.gravity, 0), 3)           as spacing_score

from lu
left join roster r1 on r1.team = lu.team and r1.k = lu.k1
left join roster r2 on r2.team = lu.team and r2.k = lu.k2
left join roster r3 on r3.team = lu.team and r3.k = lu.k3
left join roster r4 on r4.team = lu.team and r4.k = lu.k4
left join roster r5 on r5.team = lu.team and r5.k = lu.k5

-- ASSERTIONS (enforced by run.py):
-- every BBref lineup is kept
-- ASSERT == 40: SELECT count(*) FROM mart_lineup_features
-- ASSERT == 0: SELECT count(*) FROM mart_lineup_features WHERE n_covered NOT BETWEEN 0 AND 5
-- counts can never exceed covered players
-- ASSERT == 0: SELECT count(*) FROM mart_lineup_features WHERE n_shooters > n_covered
-- ASSERT == 0: SELECT count(*) FROM mart_lineup_features WHERE n_creators > n_covered
-- ASSERT == 0: SELECT count(*) FROM mart_lineup_features WHERE spacing_score IS NULL
-- ASSERT == 0: SELECT count(*) FROM mart_lineup_features WHERE minutes <= 0
-- some lineups fully covered, and some contain a rim protector
-- ASSERT > 0: SELECT count(*) FROM mart_lineup_features WHERE n_covered = 5
-- ASSERT > 0: SELECT count(*) FROM mart_lineup_features WHERE has_rim_protector
