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


# --- Calibrated talent baseline / fit residual (brief §12) -------------------
# The intuitive "fit = net - SumDPM" assumes the talent coefficient is exactly 1, which is not
# theoretically required (and is empirically false — net is concave in SumDPM). This fits a
# talent-only baseline net ~ f(SumDPM) and returns the OUT-OF-FOLD residual (actual minus the
# prediction from a model trained on OTHER teams), so "fit" is performance beyond a *calibrated*
# talent expectation rather than beyond a rigid 1:1 line. Leave-one-team-out grouping keeps a
# team's own lineups out of its baseline (lineups nest in teams). Two baselines are returned:
#   resid_linear  — talent enters linearly
#   resid_quad    — talent enters as SumDPM + SumDPM^2 (captures saturation/concavity)
# Minutes-weighted fit throughout (a 500-min lineup should anchor the curve more than a 90-min one).
def calibrated_fit_residual(
    df,
    talent="talent_sum_dpm",
    outcome="net_pts_per100",
    group="team",
    weight="minutes",
):
    """Return df with resid_linear / resid_quad: out-of-fold (leave-one-team-out) fit residuals."""
    import numpy as np

    d = df.reset_index(drop=True).copy()
    x = d[talent].to_numpy(float)
    y = d[outcome].to_numpy(float)
    w = d[weight].to_numpy(float) if weight in d else np.ones(len(d))
    groups = d[group].to_numpy()

    def wls_fit(X, yy, ww):
        # weighted least squares via normal equations; X includes intercept column
        WX = X * ww[:, None]
        return np.linalg.solve(X.T @ WX, X.T @ (ww * yy))

    for name, cols in (("resid_linear", 1), ("resid_quad", 2)):
        pred = np.full(len(d), np.nan)
        for g in np.unique(groups):
            tr, te = groups != g, groups == g
            Xtr = np.vander(x[tr], cols + 1, increasing=True)  # [1, x, x^2...]
            Xte = np.vander(x[te], cols + 1, increasing=True)
            beta = wls_fit(Xtr, y[tr], w[tr])
            pred[te] = Xte @ beta
        d[name] = y - pred
    return d


# --- Per (season, team) net rating + talent (for the pooled Analysis C) -------
# Actual net = BBref team NRtg; talent = 5 x minutes-weighted DARKO DPM. Both seasons,
# --- ShotQuality RAPM (Databallr) — PRIVATE, licensed, local-only ------------
# LICENSING: Databallr/ShotQuality is proprietary. The raw CSVs live under
# data/local/raw/databallr/ (gitignored) and are read here directly — deliberately NOT
# published to S3 (even the private marts bucket) or any mart, so the licensed data never
# leaves this machine. NEVER export ShotQuality-derived values to the public WASM site or the
# public repo. Treat exactly like CTG-derived data (private), only stricter (local-only).
#
# WHAT IT IS: ShotQuality's shot-quality RAPM — four parallel ridge regressions over ~650k
# possessions with a 3-YEAR time-decay window (2023-24 .. 2025-26, 700-day half-life). So it is
# a single blended per-player quality estimate, NOT a per-season number, and the `year`=2026 in
# the file is the decay-window END, not a season. Columns are z-scored impact metrics
# (oSQ/dSQ/cSQ offense/defense/combined; oTS/dTS/cTS), NOT points-per-100 like DPM. Use it as an
# INDEPENDENT talent axis for robustness cross-checks (standardize first), not a DPM replacement,
# and only against 2025-26 lineups (applying the 2026-ending decay window to 2024-25 would leak
# future info).
_shotquality = None


def load_shotquality():
    """ShotQuality RAPM per player (combined file) + a folded 'f. last' key. PRIVATE/local-only."""
    global _shotquality
    if _shotquality is not None:
        return _shotquality
    con = connect()
    f = (
        Path(__file__).resolve().parent.parent
        / "data/local/raw/databallr/2026-08-09/shotquality_combined_2026-08-10.csv"
    )
    if not f.exists():
        raise FileNotFoundError(
            f"ShotQuality raw not found at {f} (licensed/local-only; not in git or S3)."
        )
    _shotquality = con.execute(f"""
        select nba_id, player_name, team_abbreviation as team,
               oSQ, dSQ, cSQ, oTS, dTS, cTS, off_poss,
               regexp_replace(lower(strip_accents(
                   left(player_name,1) || '. ' ||
                   array_to_string(list_slice(string_split(player_name,' '),2,100),' ')
               )), '\\s+(jr\\.?|sr\\.?|ii|iii|iv)$', '') as flast,
               regexp_replace(lower(strip_accents(player_name)), '\\s+(jr\\.?|sr\\.?|ii|iii|iv)$', '') as fold
        from read_csv_auto('{f}')""").df()
    return _shotquality


# from raw (2024-25 team ratings are a separate pull). Lean by design — the CTG-rich
# 2-season mart_team_style is a bigger remap (2024-25 CTG is a different raw format).
_team_seasons = None


def load_team_seasons():
    """Per (season, team): actual net + actual WINS + talent (5x wmean DPM), 2024-25 & 2025-26."""
    global _team_seasons
    if _team_seasons is not None:
        return _team_seasons
    con = connect()
    con.execute("""create or replace temp table tmap as select * from (values
     ('Atlanta Hawks','ATL'),('Boston Celtics','BOS'),('Brooklyn Nets','BRK'),('Charlotte Hornets','CHO'),
     ('Chicago Bulls','CHI'),('Cleveland Cavaliers','CLE'),('Dallas Mavericks','DAL'),('Denver Nuggets','DEN'),
     ('Detroit Pistons','DET'),('Golden State Warriors','GSW'),('Houston Rockets','HOU'),('Indiana Pacers','IND'),
     ('Los Angeles Clippers','LAC'),('Los Angeles Lakers','LAL'),('Memphis Grizzlies','MEM'),('Miami Heat','MIA'),
     ('Milwaukee Bucks','MIL'),('Minnesota Timberwolves','MIN'),('New Orleans Pelicans','NOP'),('New York Knicks','NYK'),
     ('Oklahoma City Thunder','OKC'),('Orlando Magic','ORL'),('Philadelphia 76ers','PHI'),('Phoenix Suns','PHO'),
     ('Portland Trail Blazers','POR'),('Sacramento Kings','SAC'),('San Antonio Spurs','SAS'),('Toronto Raptors','TOR'),
     ('Utah Jazz','UTA'),('Washington Wizards','WAS')) as t(full_name, bbref)""")

    def block(season, ratings_csv, darko_csv):
        return f"""
          select {season} as season, tm.bbref as team, r.team_name, r.actual, r.wins, r.losses, t.talent
          from (select "Team" team_name, cast("NRtg" as double) actual,
                       cast("W" as int) wins, cast("L" as int) losses
                from read_csv_auto('{RAW}/{ratings_csv}')) r
          join (select "Team" team_name,
                  5*sum(cast(regexp_replace("DPM",'^\\+','') as double)*"MPG")/sum("MPG") talent
                from read_csv_auto('{RAW}/{darko_csv}') group by "Team") t using (team_name)
          join tmap tm on tm.full_name = r.team_name"""

    _team_seasons = con.execute(
        block(
            2026,
            "bbref/2026-07-08/league_team_ratings.csv",
            "darko/2026-07-08/darko-dpm-leaderboard.csv",
        )
        + " union all "
        + block(
            2025,
            "bbref/2026-08-07/league_team_ratings_2024-25.csv",
            "darko/2025-07-08/darko-dpm-leaderboard.csv",
        )
    ).df()
    return _team_seasons


# --- 2026-27 projected rosters (for Post 4 forward-looking) -------------------
# DARKO's preseason 2026-27 leaderboard: each player on his DARKO-assigned team with a
# projected DPM + minutes. CAVEATS: preseason DPM is integer-rounded and heavily regressed
# to the mean for mid-tier players; team assignments are DARKO's (some July 2026 moves —
# e.g. Vučević -> ORL — aren't reflected, so this is the RETURNING core; layer known moves on).
_roster27 = None


def load_roster_2027(apply_overrides=True):
    """2026-27 projected rosters from DARKO, with version-controlled roster overrides applied.

    DARKO's preseason leaderboard misses some July 2026 moves (e.g. Vučević signed with ORL but
    DARKO still lists him on BOS; Moe Wagner left ORL but is still listed there). Rather than
    hard-code fixes in a notebook cell, known corrections live in
    data/local/manual/roster_2027_overrides.csv (player, team, action add/remove, mpg_override,
    source_note) and are applied here. DARKO supplies each player's DPM (talent); the override
    only corrects team membership and minutes. Pass apply_overrides=False for the raw DARKO view.
    """
    global _roster27
    if _roster27 is not None and apply_overrides:
        return _roster27
    con = connect()
    raw = con.execute(f"""
        select "Team" team_name, "Player" player,
               cast(regexp_replace("DPM", '^\\+', '') as double) dpm, "MPG" mpg
        from read_csv_auto('{RAW}/darko/2026-08-07/darko-dpm-leaderboard.csv')""").df()
    if not apply_overrides:
        return raw
    import pandas as pd

    tmap = {"ORL": "Orlando Magic", "NOP": "New Orleans Pelicans"}
    ov_path = (
        Path(__file__).resolve().parent.parent
        / "data/local/manual/roster_2027_overrides.csv"
    )
    df = raw.copy()
    if ov_path.exists():
        ov = pd.read_csv(ov_path)
        for _, o in ov.iterrows():
            full = tmap.get(o["team"], o["team"])
            if o["action"] == "remove":
                df = df[~((df.player == o["player"]) & (df.team_name == full))]
            elif o["action"] == "add":
                # keep DARKO's DPM for this player wherever listed; move to the new team + mpg
                talent = raw.loc[raw.player == o["player"], "dpm"]
                dpm = float(talent.iloc[0]) if len(talent) else 0.0
                df = df[df.player != o["player"]]  # drop the stale-team row
                df = pd.concat(
                    [
                        df,
                        pd.DataFrame(
                            [
                                {
                                    "team_name": full,
                                    "player": o["player"],
                                    "dpm": dpm,
                                    "mpg": o["mpg_override"],
                                }
                            ]
                        ),
                    ],
                    ignore_index=True,
                )
    _roster27 = df
    return _roster27


# --- ORL/NOP roster-construction transaction history (Post 1 timeline) --------
# Hand-curated, source-cited transaction logs (one row per player per side of a move),
# version-controlled at data/local/manual/transactions_{orl,nop}.csv. Used to separate the
# three concepts the analysis keeps distinct (brief §2): roster CONSTRUCTION (who was acquired,
# when, how) is what this loader captures — as opposed to roster ARCHITECTURE (traits that
# coexist, from mart_player_league) and realized DEPLOYMENT (co-minutes, from
# mart_star_teammate_context). `era` tags each move relative to the franchise star's draft
# date (Zion 2019-06-20 / Paolo 2022-06-23): 'pre_star' = the player/move predates the star,
# 'post_star' = it came after. NEUTRAL by design — "post_star acquisition" describes timing,
# not front-office intent (we can't observe motive from a transaction).
_transactions = None
_STAR_DRAFT = {"NOP": "2019-06-20", "ORL": "2022-06-23"}  # Zion #1 / Paolo #1


def load_transactions():
    """ORL+NOP transaction history with an `era` (pre_star/post_star) tag per row."""
    global _transactions
    if _transactions is not None:
        return _transactions
    con = connect()
    root = Path(__file__).resolve().parent.parent / "data" / "local" / "manual"
    frames = []
    for team, cutoff in _STAR_DRAFT.items():
        frames.append(f"""
          select *, case when date < date '{cutoff}' then 'pre_star' else 'post_star' end as era
          from read_csv_auto('{root}/transactions_{team.lower()}.csv', header=true)""")
    _transactions = con.execute(
        " union all by name ".join(frames) + " order by date"
    ).df()
    return _transactions


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
