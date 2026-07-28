-- transform/23_mart_lineup_features.sql
-- Mart: one row per BBref 5-man lineup with engineered "fit" features.
-- This is the analytical contract for the fit thesis (v1 scope).
--
-- FEATURES (v1 — well-supported only):
--   n_shooters    — covered players whose 3PA frequency >= the LEAGUE MEDIAN
--                   (derived from stg_ctg_player_league, MIN>=500 rotation floor)
--                   AND whose 3P accuracy >= 36. Frequency-based => "floor
--                   spacing", not "best shooter" (a low-volume sniper like Bane
--                   can miss the bar; that's intended).
--   spacing_score — sum over covered players of a 3pt gravity proxy
--                   (freq_three/100 * acc_three): willingness x ability.
--   n_covered     — how many of the 5 slots resolved to a rostered player with
--                   CTG features (0-5). ~9 bench players league-wide lack CTG
--                   profiles, so some lineups are partially covered; features
--                   are computed over covered players only.
-- DEFERRED: has_rim_protector, n_creators (no staged rim-protection / usage data).
--
-- OUTCOME columns: minutes (reliable) and net_pts_per100 = BBref's signed lineup
-- differential (stg_lineups.pts). BBref gives no possession count, so this is
-- BBref's on-court net-point differential, NOT a possession-normalized rating;
-- a rigorous net rating would come from PBPStats (stg_pbp_lineups) — future work.
--
-- NAME MATCH: BBref lineup names are "F. Last"; roster names are full. One
-- normalization works for both — first-initial + '. ' + rest, accent-folded,
-- lowercased, trailing Jr./Sr./II/III/IV stripped. Validated to resolve all 20
-- rostered players (fixes Murphy III, Carter Jr., Matkovic).

with league_median as (
    select median(freq_three) as med_three_pa
    from stg_ctg_player_league
    where min >= 500
),

roster as (
    select
        team,
        regexp_replace(lower(strip_accents(
            left(player_name, 1) || '. ' ||
            array_to_string(list_slice(string_split(player_name, ' '), 2, 100), ' ')
        )), '\s+(jr\.?|sr\.?|ii|iii|iv)$', '')            as k,
        freq_three,
        acc_three,
        (freq_three / 100.0) * acc_three                   as gravity
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

    m.med_three_pa                                       as league_median_three_pa,

    -- coverage: slots resolved to a rostered player with CTG features
    (r1.k is not null)::int + (r2.k is not null)::int + (r3.k is not null)::int
        + (r4.k is not null)::int + (r5.k is not null)::int               as n_covered,

    -- shooters: covered players at/above league-median 3PA freq AND >=36% acc
    ((r1.k is not null and r1.freq_three >= m.med_three_pa and r1.acc_three >= 36))::int
        + ((r2.k is not null and r2.freq_three >= m.med_three_pa and r2.acc_three >= 36))::int
        + ((r3.k is not null and r3.freq_three >= m.med_three_pa and r3.acc_three >= 36))::int
        + ((r4.k is not null and r4.freq_three >= m.med_three_pa and r4.acc_three >= 36))::int
        + ((r5.k is not null and r5.freq_three >= m.med_three_pa and r5.acc_three >= 36))::int
                                                                          as n_shooters,

    -- spacing: sum of covered players' 3pt gravity proxy
    round(coalesce(r1.gravity, 0) + coalesce(r2.gravity, 0) + coalesce(r3.gravity, 0)
        + coalesce(r4.gravity, 0) + coalesce(r5.gravity, 0), 3)           as spacing_score

from lu
cross join league_median m
left join roster r1 on r1.team = lu.team and r1.k = lu.k1
left join roster r2 on r2.team = lu.team and r2.k = lu.k2
left join roster r3 on r3.team = lu.team and r3.k = lu.k3
left join roster r4 on r4.team = lu.team and r4.k = lu.k4
left join roster r5 on r5.team = lu.team and r5.k = lu.k5

-- ASSERTIONS (enforced by run.py):
-- every BBref lineup is kept
-- ASSERT == 40: SELECT count(*) FROM mart_lineup_features
-- ASSERT == 0: SELECT count(*) FROM mart_lineup_features WHERE n_covered NOT BETWEEN 0 AND 5
-- shooters can never exceed covered players
-- ASSERT == 0: SELECT count(*) FROM mart_lineup_features WHERE n_shooters > n_covered
-- ASSERT == 0: SELECT count(*) FROM mart_lineup_features WHERE spacing_score IS NULL
-- ASSERT == 0: SELECT count(*) FROM mart_lineup_features WHERE minutes <= 0
-- league median lands in a sane range for share-of-FGA-from-three
-- ASSERT == 0: SELECT count(*) FROM mart_lineup_features WHERE league_median_three_pa NOT BETWEEN 30 AND 50
-- at least the heavy-minute starter lineups should be fully covered
-- ASSERT > 0: SELECT count(*) FROM mart_lineup_features WHERE n_covered = 5
