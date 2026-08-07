import marimo

__generated_with = "0.23.13"
app = marimo.App(width="medium")


@app.cell
def _(mo):
    mo.md(
        """
        # marimo tour — why there's no stale state

        In a Jupyter notebook, cells share hidden mutable state and you run them in
        whatever order you click. Change a variable in cell 5, forget to re-run
        cell 9 that used it, and cell 9 now shows a **stale** value that no longer
        matches your code. The notebook lies to you.

        marimo removes that failure mode by construction. It reads your cells,
        sees which variables each one *defines* and *uses*, and builds a
        **dependency graph (DAG)**. When a value changes, marimo re-runs exactly
        the cells downstream of it — no more, no less — so what you see always
        matches the current code. Move the slider below and watch it happen.
        """
    )
    return


@app.cell
def _(mo):
    n = mo.ui.slider(1, 20, value=4, label="pick n = ")
    n
    return (n,)


@app.cell
def _(mo, n):
    # This cell USES n. marimo knows it depends on the slider, so it re-runs the
    # instant n changes — you never click "run" and never get a stale answer.
    doubled = n.value * 2
    mo.md(f"### n × 2 = **{doubled}**")
    return (doubled,)


@app.cell
def _(mo, n):
    # A SECOND consumer of n. Both this cell and the one above sit downstream of
    # the slider in the DAG, so both recompute together.
    mo.md(f"And separately: n is **{n.value}**, n² is **{n.value**2}**.")
    return


@app.cell
def _(mo):
    mo.md(
        """
        ---
        **Two rules that make this work — and that you'll feel while editing:**

        1. **A variable is defined in exactly one cell.** Try to assign `n` in
           another cell and marimo refuses — that ambiguity is the root of stale
           state, so it's simply not allowed.
        2. **Cell order on screen doesn't matter; the DAG does.** A cell runs when
           its inputs are ready, not because it's higher up.

        Next: `10_lineup_explorer.py`, which applies the house pattern — read the
        S3 marts (never raw), then drive a real analysis with UI controls.
        """
    )
    return


@app.cell
def _():
    import marimo as mo

    return (mo,)


if __name__ == "__main__":
    app.run()
