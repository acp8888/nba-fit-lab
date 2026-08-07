-- transform/05_stg_pbp_lineups_defense.sql
-- Staging: PBPStats 5-man lineup DEFENSIVE (opponent) shooting, all 30 teams
-- (league_pbpstats_lineups_5man_defense.csv, ~14.7k lineups). The gold-standard
-- rim-protection inputs — what OPPONENTS do at the rim when a lineup is on:
--   rim_freq (AtRimFrequency) = share of opponent shots taken at the rim -> DETERRENCE
--   rim_acc  (AtRimAccuracy)  = opponent FG% at the rim                  -> ALTERATION
-- For both, LOWER = better rim protection. PBPStats uses its own team codes
-- (BKN/CHA/PHX); we map them to BBref (BRK/CHO/PHO) so lineups join downstream.

select
    case "Team"
        when 'BKN' then 'BRK'
        when 'CHA' then 'CHO'
        when 'PHX' then 'PHO'
        else "Team"
    end                                          as team,
    "ShortName"                                  as short_name,
    "Minutes"                                    as minutes,
    "DefPoss"                                    as def_poss,
    "AtRimFrequency"                             as rim_freq,
    "AtRimAccuracy"                              as rim_acc,
    "AtRimFGA"                                    as rim_fga,
    2026                                         as season

from read_csv_auto(
    's3://nba-fit-lab/raw/pbpstats/2026-07-08/league_pbpstats_lineups_5man_defense.csv'
)

-- ASSERTIONS (enforced by run.py):
-- ASSERT == 14752: SELECT count(*) FROM stg_pbp_lineups_defense
-- ASSERT == 30: SELECT count(DISTINCT team) FROM stg_pbp_lineups_defense
-- team codes mapped to BBref (no BKN/CHA/PHX survive)
-- ASSERT == 0: SELECT count(*) FROM stg_pbp_lineups_defense WHERE team IN ('BKN','CHA','PHX')
-- opponent rim rates are shares/percentages in [0,1]
-- ASSERT == 0: SELECT count(*) FROM stg_pbp_lineups_defense WHERE rim_freq NOT BETWEEN 0 AND 1
-- ASSERT == 0: SELECT count(*) FROM stg_pbp_lineups_defense WHERE rim_acc NOT BETWEEN 0 AND 1
