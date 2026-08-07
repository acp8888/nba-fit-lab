-- transform/14_stg_ctg_player.sql
-- Staging: CTG top-10 player stats (shooting profile + on/off), ORL + NOP, 2026 season
-- Joins shooting frequency, shooting accuracy, and on/off efficiency exports on Player, per team.
-- Uses TRY_CAST — some players have 'N/A' in low-attempt zone stats, which CAST can't parse.

with orl_freq as (
    select * from read_csv_auto('s3://nba-fit-lab/raw/ctg/2026-07-08/orl_top10_shooting_frequency.csv')
),

orl_acc as (
    select * from read_csv_auto('s3://nba-fit-lab/raw/ctg/2026-07-08/orl_top10_shooting_accuracy.csv')
),

orl_onoff as (
    select * from read_csv_auto('s3://nba-fit-lab/raw/ctg/2026-07-08/orl_top10_onoff_efficiency.csv')
),

nop_freq as (
    select * from read_csv_auto('s3://nba-fit-lab/raw/ctg/2026-07-08/nop_top10_shooting_frequency.csv')
),

nop_acc as (
    select * from read_csv_auto('s3://nba-fit-lab/raw/ctg/2026-07-08/nop_top10_shooting_accuracy.csv')
),

nop_onoff as (
    select * from read_csv_auto('s3://nba-fit-lab/raw/ctg/2026-07-08/nop_top10_onoff_efficiency.csv')
),

orl_joined as (
    select
        orl_freq."Player"                                          as player_name,
        'ORL'                                                       as team,
        2026                                                        as season,
        orl_freq."Pos"                                              as pos,
        orl_freq."GP"                                               as gp,
        orl_freq."MPG"                                              as mpg,

        try_cast(replace(orl_freq."Rim%",        '%', '') as double)    as freq_rim,
        try_cast(replace(orl_freq."ShortMid%",   '%', '') as double)    as freq_short_mid,
        try_cast(replace(orl_freq."LongMid%",    '%', '') as double)    as freq_long_mid,
        try_cast(replace(orl_freq."Midrange%",   '%', '') as double)    as freq_midrange,
        try_cast(replace(orl_freq."Corner%",     '%', '') as double)    as freq_corner,
        try_cast(replace(orl_freq."NonCorner%",  '%', '') as double)    as freq_non_corner,
        try_cast(replace(orl_freq."Three%",      '%', '') as double)    as freq_three,

        try_cast(replace(orl_acc."RimFG%",       '%', '') as double)    as acc_rim,
        try_cast(replace(orl_acc."ShortMidFG%",  '%', '') as double)    as acc_short_mid,
        try_cast(replace(orl_acc."LongMidFG%",   '%', '') as double)    as acc_long_mid,
        try_cast(replace(orl_acc."MidrangeFG%",  '%', '') as double)    as acc_midrange,
        try_cast(replace(orl_acc."CornerFG%",    '%', '') as double)    as acc_corner,
        try_cast(replace(orl_acc."NonCornerFG%", '%', '') as double)    as acc_non_corner,
        try_cast(replace(orl_acc."ThreeFG%",     '%', '') as double)    as acc_three,

        try_cast(regexp_replace(orl_onoff."Diff",               '^\+', '') as double) as net_on_off,
        try_cast(regexp_replace(orl_onoff."Off_PtsPoss_Diff",   '^\+', '') as double) as off_pts_poss_diff,
        try_cast(regexp_replace(orl_onoff."Def_PtsPoss_Diff",   '^\+', '') as double) as def_pts_poss_diff

    from orl_freq
    join orl_acc   on orl_freq."Player" = orl_acc."Player"
    join orl_onoff on orl_freq."Player" = orl_onoff."Player"
),

nop_joined as (
    select
        nop_freq."Player"                                          as player_name,
        'NOP'                                                       as team,
        2026                                                        as season,
        nop_freq."Pos"                                              as pos,
        nop_freq."GP"                                               as gp,
        nop_freq."MPG"                                              as mpg,

        try_cast(replace(nop_freq."Rim%",        '%', '') as double)    as freq_rim,
        try_cast(replace(nop_freq."ShortMid%",   '%', '') as double)    as freq_short_mid,
        try_cast(replace(nop_freq."LongMid%",    '%', '') as double)    as freq_long_mid,
        try_cast(replace(nop_freq."Midrange%",   '%', '') as double)    as freq_midrange,
        try_cast(replace(nop_freq."Corner%",     '%', '') as double)    as freq_corner,
        try_cast(replace(nop_freq."NonCorner%",  '%', '') as double)    as freq_non_corner,
        try_cast(replace(nop_freq."Three%",      '%', '') as double)    as freq_three,

        try_cast(replace(nop_acc."RimFG%",       '%', '') as double)    as acc_rim,
        try_cast(replace(nop_acc."ShortMidFG%",  '%', '') as double)    as acc_short_mid,
        try_cast(replace(nop_acc."LongMidFG%",   '%', '') as double)    as acc_long_mid,
        try_cast(replace(nop_acc."MidrangeFG%",  '%', '') as double)    as acc_midrange,
        try_cast(replace(nop_acc."CornerFG%",    '%', '') as double)    as acc_corner,
        try_cast(replace(nop_acc."NonCornerFG%", '%', '') as double)    as acc_non_corner,
        try_cast(replace(nop_acc."ThreeFG%",     '%', '') as double)    as acc_three,

        try_cast(regexp_replace(nop_onoff."Diff",               '^\+', '') as double) as net_on_off,
        try_cast(regexp_replace(nop_onoff."Off_PtsPoss_Diff",   '^\+', '') as double) as off_pts_poss_diff,
        try_cast(regexp_replace(nop_onoff."Def_PtsPoss_Diff",   '^\+', '') as double) as def_pts_poss_diff

    from nop_freq
    join nop_acc   on nop_freq."Player" = nop_acc."Player"
    join nop_onoff on nop_freq."Player" = nop_onoff."Player"
)

select * from orl_joined
union all
select * from nop_joined

-- ASSERTIONS (enforced by run.py):
-- ASSERT == 20: SELECT count(*) FROM stg_ctg_player
-- ASSERT == 0: SELECT count(*) FROM stg_ctg_player WHERE player_name IS NULL
-- ASSERT == 0: SELECT count(*) FROM stg_ctg_player WHERE team NOT IN ('ORL', 'NOP')