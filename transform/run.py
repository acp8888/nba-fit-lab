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


def main() -> None:
    con = connect()
    sql_files = sorted(TRANSFORM_DIR.glob("[0-9]*.sql"))
    if not sql_files:
        print("No numbered .sql files found in transform/")
        sys.exit(1)

    print(f"Building {len(sql_files)} staging views...")
    all_failures: list[str] = []
    for f in sql_files:
        view = view_name(f)
        body, assert_lines = split_file(f.read_text())
        con.execute(f"CREATE OR REPLACE VIEW {view} AS {body}")
        n = con.execute(f"SELECT count(*) FROM {view}").fetchone()[0]
        print(f"  {view}: {n} rows")
        all_failures.extend(run_assertions(con, view, assert_lines))

    if all_failures:
        print(f"\n{len(all_failures)} assertion(s) FAILED:")
        for msg in all_failures:
            print(f"  - {msg}")
        sys.exit(1)
    print("\nDone — all views built, all assertions pass.")


if __name__ == "__main__":
    main()
