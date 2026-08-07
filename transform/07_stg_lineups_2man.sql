-- transform/07_stg_lineups_2man.sql
-- Staging: BBref 2-man lineup net ratings, all 30 teams, 2024-25 (season 2025).
-- PTS = the pair's on-court NET rating per 100 (team-minus-opponent margin) — same units
-- as DARKO/the 5-man mart (the other columns in the source are team-opp margins too, not
-- absolutes). Lineup arrives as "F. Last | F. Last"; we normalize each name to a lowercase,
-- accent/suffix-stripped "f. last" key so it joins player traits (09) and on/off (08).
-- Feeds mart_pair_synergy — the #2 diminishing-returns test. 2024-25 only (the season we
-- pulled pair + on/off data for; PBPStats can't produce combinations, so this is BBref).

with src as (
    select
        "Team"                                                       as team,
        string_split("Lineup", ' | ')                                as arr,
        cast(split_part("MP", ':', 1) as double)
            + cast(split_part("MP", ':', 2) as double) / 60.0        as minutes,
        cast(regexp_replace("PTS", '^\+', '') as double)             as net_pts_per100
    from read_csv_auto('s3://nba-fit-lab/raw/bbref/2025-07-08/league_lineups_2man.csv')
)

select
    team,
    regexp_replace(lower(strip_accents(trim(arr[1]))), '\s+(jr\.?|sr\.?|ii|iii|iv)$', '') as player_a,
    regexp_replace(lower(strip_accents(trim(arr[2]))), '\s+(jr\.?|sr\.?|ii|iii|iv)$', '') as player_b,
    minutes,
    net_pts_per100,
    2025                                                             as season
from src

-- ASSERTIONS (enforced by run.py):
-- ASSERT == 600: SELECT count(*) FROM stg_lineups_2man
-- ASSERT == 30: SELECT count(DISTINCT team) FROM stg_lineups_2man
-- ASSERT == 0: SELECT count(*) FROM stg_lineups_2man WHERE player_a IS NULL OR player_b IS NULL
-- ASSERT == 0: SELECT count(*) FROM stg_lineups_2man WHERE minutes <= 0
-- ASSERT == 0: SELECT count(*) FROM stg_lineups_2man WHERE player_a = player_b
