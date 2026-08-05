"""Build the staging layer: materialize each numbered .sql file as a view and
enforce its assertions.

Each transform/NN_stg_*.sql file has two parts, split by a line beginning
`-- ASSERTIONS`:

  1. A single SELECT (the view body). The view is named after the file with the
     numeric prefix stripped, e.g. 10_stg_lineups.sql -> view `stg_lineups`.
  2. Zero or more assertion lines of the form:
         -- ASSERT <op> <int>: <single-value SQL query>
     e.g. `-- ASSERT == 0: SELECT count(*) FROM stg_lineups WHERE minutes <= 0`
     op is one of == != > >= < <= (default == if omitted).

Files run in numeric order, so later files may reference earlier views. Any
assertion violation fails the whole build with a non-zero exit code.
"""

import operator
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from transform.duckdb_session import connect

TRANSFORM_DIR = Path(__file__).parent
MARTS_S3 = "s3://nba-fit-lab/marts"
ASSERT_RE = re.compile(r"--\s*ASSERT\s*(==|!=|>=|<=|>|<)?\s*(-?\d+)\s*:\s*(.+)")
OPS = {
    "==": operator.eq,
    "!=": operator.ne,
    ">": operator.gt,
    ">=": operator.ge,
    "<": operator.lt,
    "<=": operator.le,
}


def view_name(path: Path) -> str:
    # 10_stg_lineups.sql -> stg_lineups
    return path.stem.split("_", 1)[1]


def split_file(text: str) -> tuple[str, list[str]]:
    """Return (view_body_sql, [assertion_comment_lines])."""
    body_lines, assert_lines, in_asserts = [], [], False
    for line in text.splitlines():
        if line.strip().startswith("-- ASSERTIONS"):
            in_asserts = True
            continue
        (assert_lines if in_asserts else body_lines).append(line)
    body = "\n".join(body_lines).strip().rstrip(";")
    return body, assert_lines


def run_assertions(con, view: str, assert_lines: list[str]) -> list[str]:
    """Run each assertion; return a list of human-readable failures."""
    failures = []
    for line in assert_lines:
        m = ASSERT_RE.search(line)
        if not m:
            continue
        op_sym, expected_s, query = m.group(1) or "==", m.group(2), m.group(3).strip()
        expected, got = int(expected_s), con.execute(query).fetchone()[0]
        if OPS[op_sym](got, expected):
            print(f"     [PASS] {query}  ({got} {op_sym} {expected})")
        else:
            msg = f"{view}: `{query}` got {got}, expected {op_sym} {expected}"
            failures.append(msg)
            print(f"     [FAIL] {query}  (got {got}, expected {op_sym} {expected})")
    return failures


def write_mart(con, view: str) -> None:
    """Write a mart view to S3 as Parquet, one file per season partition.

    We deliberately avoid DuckDB's PARTITION_BY + OVERWRITE, which issues an
    s3:DeleteObject to clear the target — the ingest IAM role is put-only by
    design (raw layer is append-only). Instead we write each season to a fixed
    key `season=<s>/data.parquet`; re-running PUT-overwrites that same key in
    place, so re-runs stay deterministic without needing delete permission.
    The season column is dropped from the file and encoded in the path (hive
    layout), so `read_parquet(.../**/*.parquet)` recovers it. Note: a season
    that disappears between runs leaves a stale partition (we can't delete);
    seasons are only ever added here, so that doesn't arise.

    Only called for marts whose assertions pass.
    """
    seasons = [
        r[0]
        for r in con.execute(
            f"SELECT DISTINCT season FROM {view} ORDER BY season"
        ).fetchall()
    ]
    for s in seasons:
        # Fixed filename so each run PUT-overwrites the same key in place. Matches
        # DuckDB's default `data_0.parquet` so it also reclaims any file left by
        # an earlier PARTITION_BY write (which we can't delete under put-only).
        key = f"{MARTS_S3}/{view}/season={s}/data_0.parquet"
        con.execute(
            f"COPY (SELECT * EXCLUDE (season) FROM {view} WHERE season = {s}) "
            f"TO '{key}' (FORMAT PARQUET)"
        )
    print(
        f"     -> wrote {view} to {MARTS_S3}/{view} ({len(seasons)} season partition(s))"
    )


def main() -> None:
    con = connect()
    sql_files = sorted(TRANSFORM_DIR.glob("[0-9]*.sql"))
    if not sql_files:
        print("No numbered .sql files found in transform/")
        sys.exit(1)

    print(f"Building {len(sql_files)} tables...")
    all_failures: list[str] = []
    for f in sql_files:
        view = view_name(f)
        body, assert_lines = split_file(f.read_text())
        # Materialize as TABLES, not views: each S3 source is read once here, so
        # the many assertion queries (and the mart Parquet write) hit in-memory
        # tables instead of re-reading S3 every time. Data is small (tens of MB).
        con.execute(f"CREATE OR REPLACE TABLE {view} AS {body}")
        n = con.execute(f"SELECT count(*) FROM {view}").fetchone()[0]
        kind = "mart" if view.startswith("mart_") else "view"
        print(f"  {view}: {n} rows ({kind})")
        failures = run_assertions(con, view, assert_lines)
        all_failures.extend(failures)
        # Staging models stay as in-session views; marts are the published
        # contract, so persist them to S3 — but only if their assertions pass.
        if view.startswith("mart_") and not failures:
            write_mart(con, view)

    if all_failures:
        print(f"\n{len(all_failures)} assertion(s) FAILED:")
        for msg in all_failures:
            print(f"  - {msg}")
        sys.exit(1)
    print("\nDone — all tables built, all assertions pass.")


if __name__ == "__main__":
    main()
