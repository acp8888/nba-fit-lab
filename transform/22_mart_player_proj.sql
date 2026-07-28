-- transform/22_mart_player_proj.sql
-- Mart: one row per rostered ORL/NOP player (CTG top-10), joining the latest
-- DARKO impact snapshot to the player's CTG shot profile and on/off splits.
-- This is the player projection layer: faithful, no engineered threshold flags.
-- (n_shooters / n_creators / has_rim_protector belong in mart_lineup_features and
--  need a league-wide shooting baseline we haven't staged yet.)
--
-- CTG player names are normalized to DARKO's spelling for the 2 that differ.

with darko_latest as (
    select *
    from stg_darko
    where snapshot_date = (select max(snapshot_date) from stg_darko)
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

    -- CTG on/off efficiency splits
    c.net_on_off,
    c.off_pts_poss_diff,
    c.def_pts_poss_diff

from ctg_norm c
join darko_latest d on c.darko_name = d.player_name

-- ASSERTIONS (enforced by run.py):
-- every rostered player resolves to a DARKO row (alias fix + exact matches)
-- ASSERT == 20: SELECT count(*) FROM mart_player_proj
-- ASSERT == 0: SELECT count(*) FROM mart_player_proj WHERE dpm IS NULL
-- ASSERT == 0: SELECT count(*) FROM mart_player_proj WHERE player_name IS NULL
-- ASSERT == 0: SELECT count(*) FROM mart_player_proj WHERE team NOT IN ('ORL', 'NOP')
-- no dup players (one row per rostered player)
-- ASSERT == 20: SELECT count(DISTINCT player_name) FROM mart_player_proj
