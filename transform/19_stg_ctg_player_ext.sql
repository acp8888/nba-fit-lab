-- transform/19_stg_ctg_player_ext.sql
-- Staging: extra per-player CTG metrics for the ORL/NOP top-10, joining two more
-- exports per player: Offensive Overview (usage/assist -> creation) and On/Off
-- Opponent Shooting Accuracy (rim on/off -> rim protection). One row per player.
--   usage / ast_pct / tov_pct : "%"-suffixed -> double
--   ast_to_usg / psa          : already numeric
--   rim_onoff_diff            : opp rim FG% change with player ON vs OFF, signed
--                               "%" string ("-5.7%" => -5.7). Negative = opponents
--                               shoot WORSE at rim with player on (rim protection).
--   rim_onoff_pctile          : CTG percentile (0-100), higher = better rim defense
-- Player spellings match stg_ctg_player (same top-10 export set).

with orl as (
    select
        o."Player"                                                as player_name,
        'ORL'                                                     as team,
        o."Pos"                                                   as pos_ctg,
        cast(replace(o."Usage", '%', '') as double)                as usage,
        cast(replace(o."AST%",  '%', '') as double)                as ast_pct,
        o."AST:Usg"                                               as ast_to_usg,
        cast(replace(o."TOV%",  '%', '') as double)                as tov_pct,
        o."PSA"                                                   as psa,
        cast(regexp_replace(replace(r."Rim_Diff", '%', ''), '^\+', '') as double) as rim_onoff_diff,
        r."Rim_Pctile"                                            as rim_onoff_pctile
    from read_csv_auto('s3://nba-fit-lab/raw/ctg/2026-07-08/orl_top10_overview.csv') o
    join read_csv_auto('s3://nba-fit-lab/raw/ctg/2026-07-08/orl_top10_onoff_rim.csv') r
        on o."Player" = r."Player"
),

nop as (
    select
        o."Player"                                                as player_name,
        'NOP'                                                     as team,
        o."Pos"                                                   as pos_ctg,
        cast(replace(o."Usage", '%', '') as double)                as usage,
        cast(replace(o."AST%",  '%', '') as double)                as ast_pct,
        o."AST:Usg"                                               as ast_to_usg,
        cast(replace(o."TOV%",  '%', '') as double)                as tov_pct,
        o."PSA"                                                   as psa,
        cast(regexp_replace(replace(r."Rim_Diff", '%', ''), '^\+', '') as double) as rim_onoff_diff,
        r."Rim_Pctile"                                            as rim_onoff_pctile
    from read_csv_auto('s3://nba-fit-lab/raw/ctg/2026-07-08/nop_top10_overview.csv') o
    join read_csv_auto('s3://nba-fit-lab/raw/ctg/2026-07-08/nop_top10_onoff_rim.csv') r
        on o."Player" = r."Player"
)

select * from orl
union all
select * from nop

-- ASSERTIONS (enforced by run.py):
-- ASSERT == 20: SELECT count(*) FROM stg_ctg_player_ext
-- ASSERT == 0: SELECT count(*) FROM stg_ctg_player_ext WHERE usage IS NULL
-- ASSERT == 0: SELECT count(*) FROM stg_ctg_player_ext WHERE rim_onoff_pctile NOT BETWEEN 0 AND 100
-- ASSERT == 0: SELECT count(*) FROM stg_ctg_player_ext WHERE pos_ctg NOT IN ('Point','Combo','Wing','Forward','Big')
