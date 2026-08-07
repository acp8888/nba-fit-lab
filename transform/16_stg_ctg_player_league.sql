-- transform/16_stg_ctg_player_league.sql
-- Staging: CTG league-wide player shooting FREQUENCY (all players, 2025-26,
-- garbage-time filtered). Sourced from the "Leaders" view, so columns differ
-- from the per-team top10 exports: zone labels have no "%" suffix in the header
-- ("All Three" == the top10 files' "Three%"), and rank columns are interleaved.
-- Values are "%"-suffixed strings -> cast to double.
--
-- Purpose: provide the league distribution of 3PA frequency so mart_lineup_
-- features can derive the n_shooters threshold (league median) from data.
-- Traded players appear as multiple per-team stint rows (one per team).

select
    "Player"                                            as player_name,
    "Team"                                              as team_ctg,
    "Pos"                                               as pos,
    "MIN"                                               as min,
    "MPG"                                               as mpg,

    cast(replace("Rim",          '%', '') as double)     as freq_rim,
    cast(replace("Short Mid",    '%', '') as double)     as freq_short_mid,
    cast(replace("Long Mid",     '%', '') as double)     as freq_long_mid,
    cast(replace("All Mid",      '%', '') as double)     as freq_all_mid,
    cast(replace("Corner Three", '%', '') as double)     as freq_corner_three,
    cast(replace("Non Corner",   '%', '') as double)     as freq_non_corner,
    cast(replace("All Three",    '%', '') as double)     as freq_three,

    "eFG%"                                              as efg_pct,
    2026                                                as season

from read_csv_auto('s3://nba-fit-lab/raw/ctg/2026-07-08/league_player_shooting_frequency.csv')

-- ASSERTIONS (enforced by run.py):
-- ASSERT == 534: SELECT count(*) FROM stg_ctg_player_league
-- ASSERT == 0: SELECT count(*) FROM stg_ctg_player_league WHERE freq_three IS NULL
-- 3PA frequency is a percentage share of FGA
-- ASSERT == 0: SELECT count(*) FROM stg_ctg_player_league WHERE freq_three NOT BETWEEN 0 AND 100
-- rostered players must be present so the league median is comparable to them
-- ASSERT == 0: SELECT count(*) FROM stg_ctg_player_league WHERE player_name = 'Herbert Jones' AND freq_three != 52
