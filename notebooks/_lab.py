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
