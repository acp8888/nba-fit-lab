-- transform/13_stg_ctg_team.sql
-- Staging: CTG league-wide team stats, all 30 teams, 2026 season
-- Joins 9 CTG table exports on Team name, filters league-average row.
-- CTG uses full names in four_factors but city-only short names in shooting/context exports.
-- The team_map CTE normalizes everything to full name before joining.

with team_map as (
    select short_name, full_name from (values
        ('Atlanta',       'Atlanta Hawks'),
        ('Boston',        'Boston Celtics'),
        ('Brooklyn',      'Brooklyn Nets'),
        ('Charlotte',     'Charlotte Hornets'),
        ('Chicago',       'Chicago Bulls'),
        ('Cleveland',     'Cleveland Cavaliers'),
        ('Dallas',        'Dallas Mavericks'),
        ('Denver',        'Denver Nuggets'),
        ('Detroit',       'Detroit Pistons'),
        ('Golden State',  'Golden State Warriors'),
        ('Houston',       'Houston Rockets'),
        ('Indiana',       'Indiana Pacers'),
        ('LA Clippers',   'Los Angeles Clippers'),
        ('LA Lakers',     'Los Angeles Lakers'),
        ('Memphis',       'Memphis Grizzlies'),
        ('Miami',         'Miami Heat'),
        ('Milwaukee',     'Milwaukee Bucks'),
        ('Minnesota',     'Minnesota Timberwolves'),
        ('New Orleans',   'New Orleans Pelicans'),
        ('New York',      'New York Knicks'),
        ('Oklahoma City', 'Oklahoma City Thunder'),
        ('Orlando',       'Orlando Magic'),
        ('Philadelphia',  'Philadelphia 76ers'),
        ('Phoenix',       'Phoenix Suns'),
        ('Portland',      'Portland Trail Blazers'),
        ('Sacramento',    'Sacramento Kings'),
        ('San Antonio',   'San Antonio Spurs'),
        ('Toronto',       'Toronto Raptors'),
        ('Utah',          'Utah Jazz'),
        ('Washington',    'Washington Wizards')
    ) t(short_name, full_name)
),

ff as (
    select * from read_csv_auto('s3://nba-fit-lab/raw/ctg/2026-07-08/league_four_factors.csv')
    where "Rk" is not null
),

sfreq_off as (
    select * from read_csv_auto('s3://nba-fit-lab/raw/ctg/2026-07-08/league_shooting_frequency_offense.csv')
    where "Rk" is not null
),

sacc_off as (
    select * from read_csv_auto('s3://nba-fit-lab/raw/ctg/2026-07-08/league_shooting_accuracy_offense.csv')
    where "Rk" is not null
),

ctx_off_trans as (
    select * from read_csv_auto('s3://nba-fit-lab/raw/ctg/2026-07-08/league_context_offense_transition.csv')
    where "Rk" is not null
),

ctx_off_hc as (
    select * from read_csv_auto('s3://nba-fit-lab/raw/ctg/2026-07-08/league_context_offense_halfcourt_putbacks.csv')
    where "Rk" is not null
),

sfreq_def as (
    select * from read_csv_auto('s3://nba-fit-lab/raw/ctg/2026-07-08/league_shooting_frequency_defense.csv')
    where "Rk" is not null
),

sacc_def as (
    select * from read_csv_auto('s3://nba-fit-lab/raw/ctg/2026-07-08/league_shooting_accuracy_defense.csv')
    where "Rk" is not null
),

ctx_def_trans as (
    select * from read_csv_auto('s3://nba-fit-lab/raw/ctg/2026-07-08/league_context_defense_transition.csv')
    where "Rk" is not null
),

ctx_def_hc as (
    select * from read_csv_auto('s3://nba-fit-lab/raw/ctg/2026-07-08/league_context_defense_halfcourt_putbacks.csv')
    where "Rk" is not null
)

select
    ff."Team"                                                       as team_name,
    2026                                                            as season,

    -- four factors (offense)
    ff."Off_PtsPoss"                                                as off_pts_poss,
    cast(replace(ff."Off_eFG%", '%', '') as double)                  as off_efg_pct,
    cast(replace(ff."Off_TOV%", '%', '') as double)                  as off_tov_pct,
    cast(replace(ff."Off_ORB%", '%', '') as double)                  as off_orb_pct,
    ff."Off_FTRate"                                                  as off_ft_rate,

    -- four factors (defense)
    ff."Def_PtsPoss"                                                as def_pts_poss,
    cast(replace(ff."Def_eFG%", '%', '') as double)                  as def_efg_pct,
    cast(replace(ff."Def_TOV%", '%', '') as double)                  as def_tov_pct,
    cast(replace(ff."Def_ORB%", '%', '') as double)                  as def_orb_pct,
    ff."Def_FTRate"                                                  as def_ft_rate,

    -- shooting frequency offense (zone breakdown)
    cast(replace(sfreq_off."Rim",         '%', '') as double) as off_freq_rim,
    cast(replace(sfreq_off."ShortMid",    '%', '') as double) as off_freq_short_mid,
    cast(replace(sfreq_off."LongMid",     '%', '') as double) as off_freq_long_mid,
    cast(replace(sfreq_off."CornerThree", '%', '') as double) as off_freq_corner_three,
    cast(replace(sfreq_off."NonCorner",   '%', '') as double) as off_freq_non_corner_three,

    -- shooting accuracy offense (zone breakdown)
    cast(replace(sacc_off."Rim",         '%', '') as double) as off_acc_rim,
    cast(replace(sacc_off."ShortMid",    '%', '') as double) as off_acc_short_mid,
    cast(replace(sacc_off."LongMid",     '%', '') as double) as off_acc_long_mid,
    cast(replace(sacc_off."CornerThree", '%', '') as double) as off_acc_corner_three,
    cast(replace(sacc_off."NonCorner",   '%', '') as double) as off_acc_non_corner_three,

    -- shooting frequency defense
    cast(replace(sfreq_def."OppRim",         '%', '') as double) as def_freq_rim,
    cast(replace(sfreq_def."OppShortMid",    '%', '') as double) as def_freq_short_mid,
    cast(replace(sfreq_def."OppLongMid",     '%', '') as double) as def_freq_long_mid,
    cast(replace(sfreq_def."OppCornerThree", '%', '') as double) as def_freq_corner_three,
    cast(replace(sfreq_def."OppNonCorner",   '%', '') as double) as def_freq_non_corner_three,

    -- shooting accuracy defense
    cast(replace(sacc_def."OppRim",         '%', '') as double) as def_acc_rim,
    cast(replace(sacc_def."OppShortMid",    '%', '') as double) as def_acc_short_mid,
    cast(replace(sacc_def."OppLongMid",     '%', '') as double) as def_acc_long_mid,
    cast(replace(sacc_def."OppCornerThree", '%', '') as double) as def_acc_corner_three,
    cast(replace(sacc_def."OppNonCorner",   '%', '') as double) as def_acc_non_corner_three,

    -- context: offense transition
    ctx_off_trans."AllTrans_Freq"                                   as off_trans_freq,
    ctx_off_trans."AllTrans_PtsPlay"                                as off_trans_pts_per_play,
    ctx_off_trans."PtsPoss"                                         as off_total_pts_poss,

    -- context: offense halfcourt
    ctx_off_hc."HC_PtsPlay"                                         as off_hc_pts_per_play,

    -- context: defense transition
    ctx_def_trans."AllTrans_OppFreq"                                as def_trans_freq,
    ctx_def_trans."AllTrans_OppPtsPlay"                             as def_trans_pts_per_play,

    -- context: defense halfcourt
    ctx_def_hc."HC_OppPtsPlay"                                      as def_hc_pts_per_play

from ff
join sfreq_off     on ff."Team" = (select full_name from team_map where short_name = sfreq_off."Team")
join sacc_off      on ff."Team" = (select full_name from team_map where short_name = sacc_off."Team")
join ctx_off_trans on ff."Team" = (select full_name from team_map where short_name = ctx_off_trans."Team")
join ctx_off_hc    on ff."Team" = (select full_name from team_map where short_name = ctx_off_hc."Team")
join sfreq_def     on ff."Team" = (select full_name from team_map where short_name = sfreq_def."Team")
join sacc_def      on ff."Team" = (select full_name from team_map where short_name = sacc_def."Team")
join ctx_def_trans on ff."Team" = (select full_name from team_map where short_name = ctx_def_trans."Team")
join ctx_def_hc    on ff."Team" = (select full_name from team_map where short_name = ctx_def_hc."Team")

-- ASSERTIONS (enforced by run.py):
-- ASSERT == 30: SELECT count(*) FROM stg_ctg_team
-- ASSERT == 0: SELECT count(*) FROM stg_ctg_team WHERE team_name IS NULL
