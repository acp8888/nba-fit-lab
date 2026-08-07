import marimo

__generated_with = "0.23.13"
app = marimo.App(width="medium")


@app.cell
def _(mo):
    mo.md(
        """
        # Lineup explorer — does shooting fit move the needle?

        Pick a team, set a minimum-minutes filter (to fight small-sample noise),
        and a **shooter threshold**. The app splits that team's 5-man lineups into
        "enough shooters" vs "not" and compares their **minutes-weighted net
        rating**. Sample sizes are shown everywhere on purpose — with only ~20
        lineups per team, most buckets are tiny, and pretending otherwise is how
        fit analysis lies to you.
        """
    )
    return


@app.cell
def _(load_mart):
    # House pattern: read ONLY the published mart, never raw exports.
    lineups = load_mart("mart_lineup_features")
    return (lineups,)


@app.cell
def _(mo):
    team = mo.ui.dropdown(["ORL", "NOP"], value="ORL", label="team")
    min_min = mo.ui.slider(0, 150, value=0, step=10, label="min lineup minutes")
    thresh = mo.ui.slider(1, 3, value=1, label="shooter threshold (≥)")
    mo.hstack([team, min_min, thresh], justify="start", gap=2)
    return min_min, team, thresh


@app.cell
def _(lineups, min_min, pd, team):
    # Reactive filter + per-shooter-count aggregate (minutes-weighted net rating).
    df = lineups[
        (lineups["team"] == team.value) & (lineups["minutes"] >= min_min.value)
    ]

    def wnet(frame):
        m = frame["minutes"].sum()
        return (
            (frame["net_pts_per100"] * frame["minutes"]).sum() / m
            if m
            else float("nan")
        )

    rows = []
    for k, grp in df.groupby("n_shooters"):
        rows.append(
            {
                "n_shooters": int(k),
                "n_lineups": len(grp),
                "tot_min": round(grp["minutes"].sum()),
                "mw_net": round(wnet(grp), 1),
            }
        )
    by_count = pd.DataFrame(rows)
    return by_count, df, wnet


@app.cell
def _(df, mo, team, thresh, wnet):
    # Threshold split -> the headline the eventual post makes.
    T = thresh.value
    hi, lo = df[df["n_shooters"] >= T], df[df["n_shooters"] < T]
    net_hi, net_lo = wnet(hi), wnet(lo)
    gap = net_hi - net_lo

    mo.md(
        f"""
        ### {team.value}: **{net_hi:+.1f}** vs **{net_lo:+.1f}** per 100 — a
        {gap:+.1f} swing for having ≥{T} shooter(s)

        - ≥{T} shooters: **{net_hi:+.1f}**/100 · {len(hi)} lineups · {hi["minutes"].sum():.0f} min
        - <{T} shooters: **{net_lo:+.1f}**/100 · {len(lo)} lineups · {lo["minutes"].sum():.0f} min
        """
    )
    return (gap,)


@app.cell
def _(alt, by_count, gap, pd, team, thresh, team_colors):
    accent = team_colors[team.value]
    finding = (
        f"{team.value}: ≥{thresh.value} shooters worth {gap:+.1f}/100"
        if pd.notna(gap)
        else f"{team.value}: not enough lineups at this filter"
    )
    base = alt.Chart(by_count)
    zero = (
        alt.Chart(pd.DataFrame({"y": [0]}))
        .mark_rule(color="#999", strokeDash=[3, 3])
        .encode(y="y:Q")
    )
    bars = base.mark_bar(color=accent, cornerRadius=3, size=46).encode(
        x=alt.X("n_shooters:O", title="shooters in lineup"),
        y=alt.Y("mw_net:Q", title="net rating / 100 (minutes-weighted)"),
        tooltip=[
            alt.Tooltip("n_shooters:O", title="shooters"),
            alt.Tooltip("mw_net:Q", title="net/100"),
            alt.Tooltip("n_lineups:Q", title="# lineups"),
            alt.Tooltip("tot_min:Q", title="minutes"),
        ],
    )
    # sample-size label so tiny buckets are visibly low-confidence
    labels = base.mark_text(dy=-8, color="#555", fontSize=11).encode(
        x="n_shooters:O",
        y="mw_net:Q",
        text=alt.Text("tot_min:Q", format=".0f"),
    )
    (zero + bars + labels).properties(title=finding, width=440, height=300)
    return


@app.cell
def _(by_count, mo):
    mo.vstack(
        [
            mo.md("**Per-bucket detail** (labels above bars are total minutes):"),
            mo.ui.table(by_count, selection=None),
        ]
    )
    return


@app.cell
def _(mo):
    mo.md(
        """
        ---
        **Read this honestly.** These buckets are small — a "+20/100" built on two
        lineups and 70 minutes is noise, not a finding. That's *why* Phase 4 does a
        minutes-weighted regression with shrinkage toward the team mean, rather than
        trusting raw bucket averages. The explorer is here to build intuition and
        show where the sample is too thin to conclude anything.
        """
    )
    return


@app.cell
def _():
    import altair as alt
    import marimo as mo
    import pandas as pd

    from _lab import TEAM_COLORS as team_colors
    from _lab import load_mart

    return alt, load_mart, mo, pd, team_colors


if __name__ == "__main__":
    app.run()
