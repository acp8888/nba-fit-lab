-- transform/22_mart_player_proj.sql
-- Mart: one row per rostered ORL/NOP player (CTG top-10), joining DARKO impact,
-- CTG shot profile, on/off splits, and extra creation/rim-defense metrics.
-- This is the player layer: it also carries the per-player FIT FLAGS
-- (is_shooter / is_creator / is_rim_protector) that mart_lineup_features counts.
--
-- Flag definitions (thresholds derived from staged distributions, tunable):
--   is_shooter       — 3PA frequency >= league median (stg_ctg_player_league,
--                      MIN>=500 rotation floor => 41%) AND 3P accuracy >= 36.
--                      Frequency-based "floor spacing" (a low-volume sniper can
--                      miss it); sparse by design.
--   is_creator       — usage >= 24 (high self-creation) OR AST:Usg >= 1.15
--                      (pass-first creator). Catches both scorer and playmaker
--                      archetypes.
--   is_rim_protector — CTG position 'Big' AND rim on/off percentile >= 70.
--                      Gating on Big kills the on/off noise that otherwise flags
--                      small guards / injured wings (e.g. Wagner) as protectors.
--
-- CTG player names are normalized to DARKO's spelling for the 2 that differ.

with darko_latest as (
    select *
    from stg_darko
    where snapshot_date = (select max(snapshot_date) from stg_darko)
),

league as (  -- league-median 3PA frequency (rotation floor), a scalar
    select median(freq_three) as med_three_pa
    from stg_ctg_player_league
    where min >= 500
),

ctg_norm as (
    select
        *,
        case player_name
            when 'Tristan daSilva' then 'Tristan da Silva'
            when 'Wendell Carter'  then 'Wendell Carter Jr.'
            else player_name
        end as darko_name
    from stg_ctg_player
)

select
    c.team,
    c.season,
    d.player_name,
    d.position,
    e.pos_ctg,
    c.gp,
    c.mpg,

    -- DARKO impact (latest snapshot)
    d.dpm,
    d.o_dpm,
    d.d_dpm,

    -- CTG shot diet (share of FGA by zone)
    c.freq_rim,
    c.freq_short_mid,
    c.freq_long_mid,
    c.freq_midrange,
    c.freq_corner,
    c.freq_non_corner,
    c.freq_three,

    -- CTG accuracy by zone
    c.acc_rim,
    c.acc_midrange,
    c.acc_three,

    -- CTG creation profile (overview)
    e.usage,
    e.ast_pct,
    e.ast_to_usg,
    e.tov_pct,
    e.psa,

    -- CTG on/off splits (efficiency + rim defense)
    c.net_on_off,
    c.off_pts_poss_diff,
    c.def_pts_poss_diff,
    e.rim_onoff_diff,
    e.rim_onoff_pctile,

    -- engineered fit flags (counted per lineup in mart_lineup_features)
    (c.freq_three >= l.med_three_pa and c.acc_three >= 36)        as is_shooter,
    (e.usage >= 24 or e.ast_to_usg >= 1.15)                       as is_creator,
    (e.pos_ctg = 'Big' and e.rim_onoff_pctile >= 70)              as is_rim_protector

from ctg_norm c
join darko_latest d on c.darko_name = d.player_name
join stg_ctg_player_ext e on e.player_name = c.player_name and e.team = c.team
cross join league l

-- ASSERTIONS (enforced by run.py):
-- every rostered player resolves to DARKO + ext (alias fix + exact matches)
-- ASSERT == 20: SELECT count(*) FROM mart_player_proj
-- ASSERT == 0: SELECT count(*) FROM mart_player_proj WHERE dpm IS NULL
-- ASSERT == 0: SELECT count(*) FROM mart_player_proj WHERE usage IS NULL
-- ASSERT == 0: SELECT count(*) FROM mart_player_proj WHERE player_name IS NULL
-- ASSERT == 0: SELECT count(*) FROM mart_player_proj WHERE team NOT IN ('ORL', 'NOP')
-- no dup players (one row per rostered player)
-- ASSERT == 20: SELECT count(DISTINCT player_name) FROM mart_player_proj
-- flags land in sane counts (guards threshold/label regressions)
-- ASSERT == 3: SELECT count(*) FROM mart_player_proj WHERE is_rim_protector
-- ASSERT > 4: SELECT count(*) FROM mart_player_proj WHERE is_creator
