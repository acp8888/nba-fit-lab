-- transform/26_mart_pair_synergy.sql
-- Mart: 2-man pair synergy for the #2 diminishing-returns test (season 2025 / 2024-25).
-- One row per BBref 2-man lineup, with a WOWY complementarity outcome and pair TRAIT-OVERLAP
-- features, so the notebook can ask: do redundant pairs (two ball-dominant, two spacers, two
-- bigs) under-perform, and do complementary pairs over-perform?
--
-- WOWY complement — the diminishing-returns/synergy signal. For a pair (A,B) on the floor
-- together with net `nab` over `mab` minutes, and each player's overall on-court net `n`/`m`
-- from on/off, solve the player's WITHOUT-partner net:  n_A¬B = (nA*mA - nab*mab)/(mA - mab).
-- A's lift = nab - n_A¬B; complement = mean(A_lift, B_lift). We require >100 solo minutes for
-- each player so the counterfactual isn't a tiny, noisy sliver.
--
-- CAVEAT (why we also keep complement_centered): raw complement is biased POSITIVE — starters
-- play together, so a star's without-partner minutes are lower-leverage bench minutes that
-- score worse. `complement_centered` subtracts each team's mean to strip that selection effect
-- and the team-quality level; it's the column to analyze. Even centered, the 3 rotating
-- teammates on the floor remain a confound (the reason pairwise data informs but doesn't fully
-- isolate synergy — see the RAPM discussion). Finding (556 pairs, single-feature + team-FE
-- specs agree): the INTERIOR dimension — rim protection (blk_max) and size (height_min), which
-- are correlated and share one signal — predicts a positive complement; the PERIMETER overlaps
-- (usage redundancy, spacing redundancy, creator×spacer) are all null. Diminishing returns from
-- trait redundancy is essentially absent; talent dominates throughout.

with pairs as (
    select team, player_a, player_b, minutes as mab, net_pts_per100 as nab
    from stg_lineups_2man
),
joined as (
    select
        p.team, p.player_a, p.player_b, p.mab, p.nab,
        oa.on_net as na, oa.on_mp as ma,
        ob.on_net as nb, ob.on_mp as mb,
        ta.dpm as dpm_a, ta.usg as usg_a, ta.blk as blk_a, ta.height_in as ht_a, coalesce(ta.cs_gravity, 0) as csg_a,
        tb.dpm as dpm_b, tb.usg as usg_b, tb.blk as blk_b, tb.height_in as ht_b, coalesce(tb.cs_gravity, 0) as csg_b
    from pairs p
    join stg_onoff oa on oa.team = p.team and oa.player_key = p.player_a
    join stg_onoff ob on ob.team = p.team and ob.player_key = p.player_b
    join stg_player_traits ta on ta.team = p.team and ta.flast = p.player_a
    join stg_player_traits tb on tb.team = p.team and tb.flast = p.player_b
    where ma - mab > 100 and mb - mab > 100          -- enough without-partner minutes to be meaningful
      and ta.dpm is not null and tb.dpm is not null
      and ta.height_in is not null and tb.height_in is not null
),
wowy as (
    select *,
        nab - (na * ma - nab * mab) / (ma - mab)      as a_lift,
        nab - (nb * mb - nab * mab) / (mb - mab)      as b_lift
    from joined
),
feat as (
    select
        team,
        player_a, player_b,
        round(mab)                                    as minutes,
        nab                                           as together_net,
        (a_lift + b_lift) / 2.0                       as complement,
        dpm_a + dpm_b                                 as talent_sum,
        least(usg_a, usg_b)                           as usg_min,     -- both ball-dominant -> usage redundancy
        abs(usg_a - usg_b)                            as usg_gap,     -- usage hierarchy (clear roles)
        least(csg_a, csg_b)                           as csg_min,     -- both floor-spacers -> shooting redundancy
        greatest(csg_a, csg_b)                        as csg_max,     -- at least one spacer
        usg_a * csg_b + usg_b * csg_a                 as cross_cs,    -- creator x spacer complementarity
        least(ht_a, ht_b)                             as height_min,  -- both tall -> size stacking
        least(blk_a, blk_b)                           as blk_min,     -- both rim protectors -> redundancy
        greatest(blk_a, blk_b)                        as blk_max,     -- at least one rim protector
        2025                                          as season
    from wowy
)

select
    * exclude (season),
    complement - avg(complement) over (partition by team)  as complement_centered,
    season
from feat

-- ASSERTIONS (enforced by run.py):
-- ASSERT > 350: SELECT count(*) FROM mart_pair_synergy
-- ASSERT == 30: SELECT count(DISTINCT team) FROM mart_pair_synergy
-- ASSERT == 0: SELECT count(*) FROM mart_pair_synergy WHERE complement IS NULL
-- ASSERT == 0: SELECT count(*) FROM mart_pair_synergy WHERE talent_sum IS NULL
-- within-team centering nets to ~0 per team (rounds to 0 summed leaguewide)
-- ASSERT == 0: SELECT round(sum(complement_centered)) FROM mart_pair_synergy
-- outcome in a sane band (guards the WOWY division)
-- ASSERT == 0: SELECT count(*) FROM mart_pair_synergy WHERE complement NOT BETWEEN -60 AND 60
