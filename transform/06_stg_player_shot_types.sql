-- transform/06_stg_player_shot_types.sql
-- Staging: NBA.com player tracking shot types (catch-and-shoot vs pull-up), for a
-- principled floor-SPACING measure. Catch-and-shoot threes are the spacing-relevant
-- subset (stationary, off-ball); pull-up threes are self-creation.
--   cs_gravity = catch-and-shoot 3PA per-36 min  x  catch-and-shoot 3P%
--              = expected C&S 3 makes per 36 -> how much a player punishes an open
--                off-ball look (higher = more floor-spacing threat)
--   cs_share   = C&S 3PA / (C&S + pull-up 3PA) -> spacer (high) vs creator (low)
-- NBA.com uses standard codes (BKN/CHA/PHX); mapped to BBref (BRK/CHO/PHO).

select
    "Player"                                                     as player_name,
    case "Team"
        when 'BKN' then 'BRK' when 'CHA' then 'CHO' when 'PHX' then 'PHO'
        else "Team"
    end                                                          as team,
    "GP"                                                         as gp,
    "MIN"                                                        as min,
    -- 0 for players with no minutes or no catch-and-shoot 3s (no spacing threat)
    coalesce(
        ("CS_FG3A"::double / nullif("MIN", 0) * 36.0) * "CS_FG3_PCT"::double,
        0
    )                                                            as cs_gravity,
    "CS_FG3A"::double / nullif("CS_FG3A" + "PU_FG3A", 0)          as cs_share,
    "CS_FG3A"                                                    as cs_fg3a,
    "CS_FG3_PCT"                                                 as cs_fg3_pct,
    2026                                                         as season

from read_csv_auto('s3://nba-fit-lab/raw/nbastats/2026-07-08/league_player_shot_types.csv')

-- ASSERTIONS (enforced by run.py):
-- ASSERT == 582: SELECT count(*) FROM stg_player_shot_types
-- ASSERT == 0: SELECT count(*) FROM stg_player_shot_types WHERE cs_gravity IS NULL
-- catch-and-shoot gravity is a non-negative rate; elite spacers ~2.5-3, small-
-- sample flukes higher (band guards against parse errors, not outliers)
-- ASSERT == 0: SELECT count(*) FROM stg_player_shot_types WHERE cs_gravity NOT BETWEEN 0 AND 12
