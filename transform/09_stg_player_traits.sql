-- transform/09_stg_player_traits.sql
-- Staging: per-player 2024-25 traits (season 2025) for the pair-synergy mart, one row per
-- (BBref team, "f. last" key). Bundles the fit-relevant traits from four public sources:
--   dpm       (DARKO, joined on full name + full team name)
--   usg, blk  (BBref Advanced, USG% / BLK%)
--   height_in (BBref heights, "6-9" -> inches)
--   cs_gravity(NBA.com catch-and-shoot: C&S 3PA-per-36 x C&S 3P% -> floor-spacing threat)
-- Mirrors the attr assembly in mart_lineup_features_league, but for 2024-25 and keyed to the
-- "f. last" form the 2-man lineups / on-off use. On the rare "f. last" collision within a
-- team, keep the higher-minutes player (the star). Feeds mart_pair_synergy only.

with adv as (
    select
        "Team"                                       as team,
        regexp_replace(lower(strip_accents(
            left("Player", 1) || '. ' ||
            array_to_string(list_slice(string_split("Player", ' '), 2, 100), ' ')
        )), '\s+(jr\.?|sr\.?|ii|iii|iv)$', '')       as flast,
        regexp_replace(lower(strip_accents("Player")), '\s+(jr\.?|sr\.?|ii|iii|iv)$', '') as fold,
        cast("USG%" as double)                       as usg,
        cast("BLK%" as double)                       as blk,
        cast("MP" as int)                            as mp
    from read_csv('s3://nba-fit-lab/raw/bbref/2025-07-08/league_player_advanced.csv', skip = 4)
    where "Team" in (select bbref_abbr from stg_team_map)
),
dk as (
    select regexp_replace(lower(strip_accents("Player")), '\s+(jr\.?|sr\.?|ii|iii|iv)$', '') as fold,
        "Team"                                       as team,
        cast(regexp_replace("DPM", '^\+', '') as double) as dpm
    from read_csv_auto('s3://nba-fit-lab/raw/darko/2025-07-08/darko-dpm-leaderboard.csv')
),
ht as (
    select regexp_replace(lower(strip_accents("Player")), '\s+(jr\.?|sr\.?|ii|iii|iv)$', '') as fold,
        "Team"                                       as team_bbref,
        cast(split_part("Ht", '-', 1) as int) * 12 + cast(split_part("Ht", '-', 2) as int) as height_in
    from read_csv_auto('s3://nba-fit-lab/raw/bbref/2025-07-08/league_player_heights.csv')
),
st as (
    select regexp_replace(lower(strip_accents("Player")), '\s+(jr\.?|sr\.?|ii|iii|iv)$', '') as fold,
        case "Team" when 'BKN' then 'BRK' when 'CHA' then 'CHO' when 'PHX' then 'PHO' else "Team" end as team,
        coalesce(("CS_FG3A"::double / nullif("MIN", 0) * 36.0) * "CS_FG3_PCT"::double, 0) as cs_gravity
    from read_csv_auto('s3://nba-fit-lab/raw/nbastats/2025-07-08/league_player_shot_types.csv')
)

select
    adv.team,
    adv.flast,
    dk.dpm,
    adv.usg,
    adv.blk,
    ht.height_in,
    st.cs_gravity,
    2025                                             as season
from adv
join stg_team_map tm on adv.team = tm.bbref_abbr
left join dk on dk.fold = adv.fold and dk.team = tm.full_name
left join ht on ht.fold = adv.fold and ht.team_bbref = adv.team
left join st on st.fold = adv.fold and st.team = adv.team
qualify row_number() over (partition by adv.team, adv.flast order by adv.mp desc) = 1

-- ASSERTIONS (enforced by run.py):
-- ASSERT > 650: SELECT count(*) FROM stg_player_traits
-- ASSERT == 30: SELECT count(DISTINCT team) FROM stg_player_traits
-- ASSERT == 0: SELECT count(*) FROM stg_player_traits WHERE flast IS NULL
-- one row per (team, f.last) — no duplicate keys survive the qualify
-- ASSERT == 0: SELECT count(*) - count(DISTINCT (team, flast)) FROM stg_player_traits
-- traits in sane bands where present (guards joins/parse); nulls allowed (partial coverage)
-- ASSERT == 0: SELECT count(*) FROM stg_player_traits WHERE usg NOT BETWEEN 0 AND 60
-- ASSERT == 0: SELECT count(*) FROM stg_player_traits WHERE height_in IS NOT NULL AND height_in NOT BETWEEN 60 AND 90
-- ASSERT == 0: SELECT count(*) FROM stg_player_traits WHERE cs_gravity IS NOT NULL AND cs_gravity NOT BETWEEN 0 AND 12
