-- transform/08_stg_onoff.sql
-- Staging: BBref player On/Off, all 30 teams, 2024-25 (season 2025). We keep only the
-- ON-COURT split: Diff_ORtg is that player's on-court NET rating (Team_ORtg - Opp_ORtg),
-- earned over on-court minutes (MP). Combined in mart_pair_synergy with a pair's together-
-- minutes to solve each player's WITHOUT-partner net (the WOWY decomposition). Player is
-- normalized to the same "f. last" key used by stg_lineups_2man / stg_player_traits.

select
    "Team"                                                          as team,
    regexp_replace(lower(strip_accents(
        left("Player", 1) || '. ' ||
        array_to_string(list_slice(string_split("Player", ' '), 2, 100), ' ')
    )), '\s+(jr\.?|sr\.?|ii|iii|iv)$', '')                          as player_key,
    -- Diff_ORtg arrives as a signed string ("+0.5"/"-3.4"); strip the leading +.
    cast(regexp_replace(cast("Diff_ORtg" as varchar), '^\+', '') as double) as on_net,
    cast("MP" as double)                                            as on_mp,
    2025                                                            as season
from read_csv_auto('s3://nba-fit-lab/raw/bbref/2025-07-08/league_onoff.csv')
where "Split" = 'On Court'

-- ASSERTIONS (enforced by run.py):
-- ASSERT == 654: SELECT count(*) FROM stg_onoff
-- ASSERT == 30: SELECT count(DISTINCT team) FROM stg_onoff
-- ASSERT == 0: SELECT count(*) FROM stg_onoff WHERE player_key IS NULL
-- ASSERT == 0: SELECT count(*) FROM stg_onoff WHERE on_net IS NULL
-- on-court net ratings within BBref's own bounds (guards the signed-string parse; low-minute
-- players legitimately hit +/-100, and never clear the 100-min pair threshold in the mart)
-- ASSERT == 0: SELECT count(*) FROM stg_onoff WHERE on_net NOT BETWEEN -100 AND 100
-- ASSERT == 0: SELECT count(*) FROM stg_onoff WHERE on_mp <= 0
