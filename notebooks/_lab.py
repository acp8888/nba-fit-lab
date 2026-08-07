"""Shared data access for the analysis notebooks (the "house pattern").

Notebooks read ONLY the published marts on S3 — never raw exports. This keeps the
cleaning/modeling contract in the transform layer and the notebooks purely about
analysis. One DuckDB connection (with the S3 secret) is reused across loads.

Usage in a notebook's first cell:
    from _lab import load_mart
    lineups = load_mart("mart_lineup_features")
"""

import sys
from pathlib import Path

# make the repo root importable so we can reuse the transform S3 connection
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from transform.duckdb_session import connect

MARTS = "s3://nba-fit-lab/marts"

# Project team palette — validated categorical pair (CVD ΔE 23.1, passes the
# dataviz six-checks in light mode). Reuse everywhere so team identity is
# consistent across charts. Revalidate against the dark surface before publishing.
TEAM_COLORS = {"ORL": "#0A7CD6", "NOP": "#E03A3E"}

_con = None


def _connection():
    global _con
    if _con is None:
        _con = connect()
    return _con


def load_mart(name: str):
    """Load a published mart (all season partitions) into a pandas DataFrame."""
    con = _connection()
    return con.execute(
        f"select * from read_parquet('{MARTS}/{name}/**/*.parquet')"
    ).df()


# --- Held-out 2024-25 five-man features (for the A2 replication section) ------
# mart_lineup_features_league is the CURRENT season (2025-26) only; the 2024-25
# prior-season pull was ingested to raw for a held-out replication but deliberately
# NOT folded into that mart (its consumers assume one season). This rebuilds the
# SAME feature set from the 2024-25 raw, via the same code path, so the notebook can
# show the replication live. No CTG in 2024-25 (licensing) -> spacing uses NBA.com
# catch-and-shoot only, which is the A2 spacing measure anyway.
_2024 = None


def load_5man_features_2024():
    """2024-25 leaguewide 5-man lineup features, rebuilt from raw (held-out season)."""
    global _2024
    if _2024 is not None:
        return _2024
    con = connect()

    def fold(c):
        return (
            r"regexp_replace(lower(strip_accents("
            + c
            + r")), '\s+(jr\.?|sr\.?|ii|iii|iv)$', '')"
        )

    def flast(c):
        return (
            r"regexp_replace(lower(strip_accents(left(" + c + r",1)||'. '||"
            r"array_to_string(list_slice(string_split("
            + c
            + r",' '),2,100),' '))), '\s+(jr\.?|sr\.?|ii|iii|iv)$', '')"
        )

    r = f"{RAW}/%s/2025-07-08/%s"
    con.execute("""create or replace temp table tmap as select * from (values
     ('Atlanta Hawks','ATL'),('Boston Celtics','BOS'),('Brooklyn Nets','BRK'),('Charlotte Hornets','CHO'),
     ('Chicago Bulls','CHI'),('Cleveland Cavaliers','CLE'),('Dallas Mavericks','DAL'),('Denver Nuggets','DEN'),
     ('Detroit Pistons','DET'),('Golden State Warriors','GSW'),('Houston Rockets','HOU'),('Indiana Pacers','IND'),
     ('Los Angeles Clippers','LAC'),('Los Angeles Lakers','LAL'),('Memphis Grizzlies','MEM'),('Miami Heat','MIA'),
     ('Milwaukee Bucks','MIL'),('Minnesota Timberwolves','MIN'),('New Orleans Pelicans','NOP'),('New York Knicks','NYK'),
     ('Oklahoma City Thunder','OKC'),('Orlando Magic','ORL'),('Philadelphia 76ers','PHI'),('Phoenix Suns','PHO'),
     ('Portland Trail Blazers','POR'),('Sacramento Kings','SAC'),('San Antonio Spurs','SAS'),('Toronto Raptors','TOR'),
     ('Utah Jazz','UTA'),('Washington Wizards','WAS')) as t(full_name, bbref)""")
    con.execute(f"""create or replace temp table adv as
      select "Team" team, {fold('"Player"')} fold, {flast('"Player"')} flast,
             cast("USG%" as double) usg, cast("AST%" as double) ast_pct, cast("BLK%" as double) blk_pct, cast("MP" as int) mp
      from read_csv('{r % ("bbref", "league_player_advanced.csv")}', skip=4)
      where "Team" in (select bbref from tmap)""")
    con.execute(f"""create or replace temp table dk as
      select {fold('"Player"')} fold, "Team" team, cast(regexp_replace("DPM",'^\\+','') as double) dpm
      from read_csv_auto('{r % ("darko", "darko-dpm-leaderboard.csv")}')""")
    con.execute(f"""create or replace temp table ht as
      select {fold('"Player"')} fold, "Team" team_bbref,
             cast(split_part("Ht",'-',1) as int)*12 + cast(split_part("Ht",'-',2) as int) height_in
      from read_csv_auto('{r % ("bbref", "league_player_heights.csv")}')""")
    con.execute(f"""create or replace temp table st as
      select {fold('"Player"')} fold,
        case "Team" when 'BKN' then 'BRK' when 'CHA' then 'CHO' when 'PHX' then 'PHO' else "Team" end team,
        coalesce(("CS_FG3A"::double/nullif("MIN",0)*36.0)*"CS_FG3_PCT"::double, 0) cs_gravity
      from read_csv_auto('{r % ("nbastats", "league_player_shot_types.csv")}')""")
    con.execute(f"""create or replace temp table pdef as
      select case "Team" when 'BKN' then 'BRK' when 'CHA' then 'CHO' when 'PHX' then 'PHO' else "Team" end team,
        array_to_string(list_sort(list_transform(string_split("ShortName", ', '), x -> {fold("x")})), '|') k,
        "Minutes" dmin, "AtRimFrequency" rim_freq, "AtRimAccuracy" rim_acc
      from read_csv_auto('{r % ("pbpstats", "league_pbpstats_lineups_5man_defense.csv")}')""")
    con.execute(f"""create or replace temp table lug as
      with s as (select "Team" team, list_sort(string_split("Lineup",' | ')) arr,
                   (cast(split_part("MP",':',1) as double)+cast(split_part("MP",':',2) as double)/60.0) as mins,
                   cast(regexp_replace("PTS",'^\\+','') as double) as net
                 from read_csv_auto('{r % ("bbref", "league_lineups_5man.csv")}'))
      select row_number() over () lineup_id, team, array_to_string(arr,'|') lineup_key, mins as minutes, net,
        arr[1] p1, arr[2] p2, arr[3] p3, arr[4] p4, arr[5] p5 from s""")
    con.execute("""create or replace temp table attr as
      select adv.team, adv.flast k, dk.dpm, adv.usg, adv.ast_pct, ht.height_in, st.cs_gravity
      from adv join tmap tm on adv.team = tm.bbref
      left join dk on dk.fold = adv.fold and dk.team = tm.full_name
      left join ht on ht.fold = adv.fold and ht.team_bbref = adv.team
      left join st on st.fold = adv.fold and st.team = adv.team
      qualify row_number() over (partition by adv.team, adv.flast order by adv.mp desc) = 1""")
    con.execute(f"""create or replace temp table lu as
      select lineup_id, lineup_key, team, minutes, net,
        unnest([{flast("p1")},{flast("p2")},{flast("p3")},{flast("p4")},{flast("p5")}]) k from lug""")
    con.execute("""create or replace temp table base as
      select lu.lineup_id, any_value(lu.team) team, any_value(lu.minutes) as minutes,
        any_value(lu.net) as net_pts_per100, count(a.k) n_covered, sum(a.dpm) talent_sum_dpm,
        avg(a.cs_gravity) spacing_cs_mean, avg(a.height_in) avg_height_in,
        stddev_pop(a.usg) usg_spread, max(a.ast_pct) ast_max,
        array_to_string(list_sort(list_transform(string_split(any_value(lu.lineup_key),'|'),
          t -> regexp_replace(lower(strip_accents(regexp_replace(t,'^[A-Za-z]\\.\\s+',''))),'\\s+(jr\\.?|sr\\.?|ii|iii|iv)$',''))),'|') lastname_key
      from lu left join attr a on a.team=lu.team and a.k=lu.k group by lu.lineup_id""")
    con.execute("""create or replace temp table rim as
      select lineup_id, rim_freq, rim_acc from (
        select base.lineup_id, p.rim_freq, p.rim_acc,
          row_number() over (partition by base.lineup_id order by abs(base.minutes-p.dmin)) rn
        from base join pdef p on p.team=base.team and p.k=base.lastname_key) where rn=1""")
    _2024 = con.execute("""select base.* exclude(lineup_id,lastname_key),
        -(r.rim_freq*r.rim_acc) rim_suppress, 2025 as season
      from base left join rim r on r.lineup_id=base.lineup_id""").df()
    return _2024


# --- Per-game rim protection (for the A3 swing-game resolution) ---------------
# Per-game opponent (defense) + own (offense) at-rim scoring for ORL/NOP, 2025-26,
# from PBPStats opponent/team shot-distribution game logs. Raw-read exception like
# load_5man_features_2024 — this is game-level input for the fit-win/loss check, not
# a mart. rim_suppress_game = -(rim frequency x rim accuracy) allowed (higher = better).
_games_rim = None


def load_games_rim():
    """Per-game rim for ORL & NOP: (team, date, rim_suppress_game, own_rim)."""
    global _games_rim
    if _games_rim is not None:
        return _games_rim
    con = connect()

    def one(t):
        opp = f"{RAW}/pbpstats/2026-07-08/pbpstats_opp_gamelog_shotdist_{t}.csv"
        own = f"{RAW}/pbpstats/2026-07-08/pbpstats_team_gamelog_shotdist_{t}.csv"
        return f"""select '{t}' as team, o."Date"::varchar as date,
                   -(o."AtRimFrequency" * o."AtRimAccuracy") as rim_suppress_game,
                   (m."AtRimFrequency" * m."AtRimAccuracy") as own_rim
            from read_csv_auto('{opp}') o
            join read_csv_auto('{own}') m on m."Date" = o."Date" """

    _games_rim = con.execute(one("ORL") + " union all " + one("NOP")).df()
    return _games_rim


# --- Lineage access (for the data-walkthrough notebook only) -----------------
# The house pattern says notebooks read marts, not raw/staging. The walkthrough
# is the deliberate exception: it explains raw -> staging -> mart, so it needs to
# query the staging views too. This builds every numbered transform/*.sql as a
# view in one connection (cheap — views are lazy; queries hit S3).
_lineage_con = None
RAW = "s3://nba-fit-lab/raw"


def lineage_con():
    """A DuckDB connection with every stg_*/mart_* view built, for lineage queries."""
    global _lineage_con
    if _lineage_con is None:
        from transform.run import split_file, view_name

        c = connect()
        tdir = Path(__file__).resolve().parent.parent / "transform"
        # materialize as tables (read each S3 source once) so repeated lineage
        # queries in the walkthrough hit memory instead of re-reading S3
        for f in sorted(tdir.glob("[0-9]*.sql")):
            c.execute(
                f"create or replace table {view_name(f)} as {split_file(f.read_text())[0]}"
            )
        _lineage_con = c
    return _lineage_con


def q(sql: str):
    """Run SQL against the lineage connection; return a DataFrame."""
    return lineage_con().execute(sql).df()


def tables() -> list[str]:
    """Names of the staging + mart views, in build order."""
    from transform.run import view_name

    tdir = Path(__file__).resolve().parent.parent / "transform"
    return [view_name(f) for f in sorted(tdir.glob("[0-9]*.sql"))]
