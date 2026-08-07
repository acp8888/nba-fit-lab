-- transform/18_stg_player_heights.sql
-- Staging: BBref player heights/weights compiled across all 30 team rosters.
-- Feeds a minutes-weighted team size in mart_team_style (weights come from DARKO
-- minutes). Ht arrives as "6-9" (feet-inches) -> total inches. Traded players
-- appear on more than one team roster (real; resolved by team when weighting).

select
    "Player"                                                        as player_name,
    "Team"                                                          as team_bbref,
    "Pos"                                                           as pos,
    cast(split_part("Ht", '-', 1) as int) * 12
        + cast(split_part("Ht", '-', 2) as int)                     as height_in,
    cast("Wt" as int)                                               as weight_lb,
    2026                                                            as season

from read_csv_auto('s3://nba-fit-lab/raw/bbref/2026-07-08/league_player_heights.csv')

-- ASSERTIONS (enforced by run.py):
-- ASSERT == 661: SELECT count(*) FROM stg_player_heights
-- ASSERT == 0: SELECT count(*) FROM stg_player_heights WHERE player_name IS NULL
-- NBA player heights span ~5'7"-7'4"; guards the "6-9" -> inches parse
-- ASSERT == 0: SELECT count(*) FROM stg_player_heights WHERE height_in NOT BETWEEN 60 AND 90
-- every roster row carries a known BBref team code
-- ASSERT == 0: SELECT count(*) FROM stg_player_heights WHERE team_bbref NOT IN (SELECT bbref_abbr FROM stg_team_map)
