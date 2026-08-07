-- transform/02_stg_player_advanced.sql
-- Staging: BBref league-wide player Advanced stats (all players, all teams).
-- Leaguewide base for fit features (creation: USG%/AST%; rim: BLK%/DRB%) and a
-- shooting-willingness proxy (3PAr). Public-source (BBref), so usable in the
-- eventual public companion app.
--
-- BBref "Get table as CSV": citation + blanks, real header on row 5 -> skip 4.
-- Values are plain numbers (USG% "20.4", TS%/3PAr as ".594"/".111"). Traded
-- players get a combined 2TM/3TM/4TM row plus one row per team; we keep only the
-- real per-team rows so a player's stats join to that team's lineups.

select
    "Player"                                    as player_name,
    "Team"                                       as team_bbref,
    "Pos"                                        as pos,
    cast("G" as int)                             as g,
    cast("MP" as int)                            as mp,
    cast("USG%" as double)                       as usg,
    cast("AST%" as double)                       as ast_pct,
    cast("BLK%" as double)                       as blk_pct,
    cast("DRB%" as double)                       as drb_pct,
    cast("TS%" as double)                        as ts_pct,
    cast("3PAr" as double)                       as three_pa_rate,
    2026                                         as season

from read_csv(
    's3://nba-fit-lab/raw/bbref/2026-07-08/league_player_advanced.csv',
    skip = 4
)
where "Team" in (select bbref_abbr from stg_team_map)

-- ASSERTIONS (enforced by run.py):
-- one row per player-team stint across the league
-- ASSERT > 600: SELECT count(*) FROM stg_player_advanced
-- ASSERT == 0: SELECT count(*) FROM stg_player_advanced WHERE player_name IS NULL
-- ASSERT == 0: SELECT count(*) FROM stg_player_advanced WHERE usg IS NULL
-- combined 2TM/3TM/4TM rows must be excluded (all teams are real codes)
-- ASSERT == 30: SELECT count(DISTINCT team_bbref) FROM stg_player_advanced
-- rate stats in sane bands
-- ASSERT == 0: SELECT count(*) FROM stg_player_advanced WHERE usg NOT BETWEEN 0 AND 60
-- ASSERT == 0: SELECT count(*) FROM stg_player_advanced WHERE three_pa_rate NOT BETWEEN 0 AND 1
