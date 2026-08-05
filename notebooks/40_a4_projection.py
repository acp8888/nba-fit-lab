import marimo

__generated_with = "0.23.13"
app = marimo.App(width="medium")


@app.cell
def _(mo):
    mo.md(
        """
        # A4 — Roster projection: talent, fit, and a *distribution* of wins

        Chain: each player's **DARKO DPM** × his minutes → team net rating →
        **Pythagorean wins**. Then two honest add-ons: a small **fit** bump from
        A2's rim-protection coefficient, and — the real point — we don't report a
        single number. We simulate the season thousands of times (players' DPM and
        minutes are uncertain) and report a **win distribution**.

        The engine is calibrated: it retrodicts ORL ≈ 44 (actual 45) and NOP ≈ 28
        (actual 26) from last season's rosters.
        """
    )
    return


@app.cell
def _(load_mart):
    roster = load_mart("mart_roster")
    lineups = load_mart("mart_lineup_features_league")
    return lineups, roster


@app.cell
def _(lineups, np):
    # A2 rim-protection coefficient (raw, per unit rim_suppress) — see
    # notebooks/20_a2_scarcity. The fit effect BEYOND talent, applied
    # CONSERVATIVELY (half) on top of the DPM projection.
    RIM_COEF, CONSERV = 75.2, 0.5

    # team rim-protection level (minutes-weighted rim_suppress = opponent rim
    # scoring suppressed; higher = better) and the league average, from A2.
    lu = lineups.dropna(subset=["rim_suppress"]).copy()
    tr = lu.groupby("team").apply(
        lambda x: (x["rim_suppress"] * x["minutes"]).sum() / x["minutes"].sum(),
        include_groups=False,
    )
    team_rim = tr.to_dict()
    league_rim = float(np.mean(list(team_rim.values())))
    return CONSERV, RIM_COEF, league_rim, team_rim


@app.cell
def _(mo):
    team = mo.ui.dropdown(["ORL", "NOP"], value="ORL", label="team")
    talent_delta = mo.ui.slider(
        -5, 5, value=0, step=0.5, label="roster move: Δ net from talent"
    )
    rim_delta = mo.ui.slider(
        -3, 3, value=0, step=0.5, label="roster move: Δ net from rim protection"
    )
    mo.hstack([team, talent_delta, rim_delta], justify="start", gap=2)
    return rim_delta, talent_delta, team


@app.cell
def _(
    CONSERV, RIM_COEF, league_rim, np, rim_delta, roster, talent_delta, team, team_rim
):
    def pyth_wins(net, exp=13.91, ppg=115.0):
        pf, pa = ppg + net / 2.0, ppg - net / 2.0
        return 82 * pf**exp / (pf**exp + pa**exp)

    r = roster[roster["team"] == team.value]
    dpm, w = r["dpm"].to_numpy(float), r["mpg"].to_numpy(float)

    base_net = 5 * (dpm * w).sum() / w.sum()  # talent-only projection
    fit_net = RIM_COEF * CONSERV * (team_rim[team.value] - league_rim)  # A2 fit bump
    move_net = talent_delta.value + rim_delta.value  # user's move (both in net/100)
    proj_net = base_net + fit_net + move_net

    # uncertainty: player DPM ~ N(dpm, 1.2), minutes vary lognormally (injuries/role)
    rng = np.random.default_rng(0)
    N = 5000
    dpm_d = dpm + rng.normal(0, 1.2, size=(N, len(dpm)))
    min_d = w * np.exp(rng.normal(0, 0.15, size=(N, len(w))))
    net_d = 5 * (dpm_d * min_d).sum(1) / min_d.sum(1) + fit_net + move_net
    wins_d = pyth_wins(net_d)

    p5, p50, p95 = np.percentile(wins_d, [5, 50, 95])
    p_playoff = float((wins_d >= 42).mean())
    # wins per +1 net rating (same whatever the source), for pricing moves
    dwin_per_net = pyth_wins(proj_net + 1) - pyth_wins(proj_net)
    return (
        base_net,
        dwin_per_net,
        fit_net,
        p5,
        p50,
        p95,
        p_playoff,
        proj_net,
        pyth_wins,
        wins_d,
    )


@app.cell
def _(base_net, fit_net, mo, p5, p50, p95, p_playoff, proj_net, pyth_wins, team):
    mo.md(
        f"""
        ### {team.value}: **{p50:.0f} wins** (90% range **{p5:.0f}–{p95:.0f}**)

        - talent only (ΣDPM → Pythagorean): **{pyth_wins(base_net):.0f} wins** ({base_net:+.1f} net)
        - + A2 fit bump: **{fit_net:+.1f}** net → projection **{proj_net:+.1f}** net
        - probability of ≥42 wins (play-in range): **{p_playoff:.0%}**

        The headline is the **range**, not the point. A ~{(p95 - p5):.0f}-win 90%
        interval is the honest width once you admit DPM and minutes are uncertain.
        """
    )
    return


@app.cell
def _(alt, pd, team, team_colors, wins_d):
    hist = pd.DataFrame({"wins": wins_d})
    accent = team_colors[team.value]
    chart = (
        alt.Chart(hist)
        .mark_bar(color=accent, opacity=0.85)
        .encode(
            x=alt.X("wins:Q", bin=alt.Bin(maxbins=40), title="simulated season wins"),
            y=alt.Y("count():Q", title="simulations"),
            tooltip=[alt.Tooltip("count():Q", title="sims")],
        )
    )
    rule = (
        alt.Chart(pd.DataFrame({"w": [42]}))
        .mark_rule(color="#c0392b", strokeDash=[4, 4])
        .encode(x="w:Q")
    )
    (chart + rule).properties(
        title=f"{team.value}: distribution of projected wins (red line = 42, play-in range)",
        width=460,
        height=280,
    )
    return


@app.cell
def _(dwin_per_net, fit_net, mo, team):
    mo.md(
        f"""
        ### Pricing a roster move

        - **+1 net rating** (from talent *or* rim protection) ≈ **{dwin_per_net:.1f} wins**.
        - {team.value}'s built-in **fit adjustment** — its rim protection vs the
          league — is **{fit_net:+.1f} net** (~{fit_net * dwin_per_net:+.1f} wins).

        The asymmetry isn't the conversion; it's what's *available*. A talent trade
        realistically swings ±3–5 net; overhauling rim protection from average to
        elite is worth ~+2.6. So **talent sets the season and fit is the fine
        print** — and note the *direct* rim measure says NOP's rim protection is
        genuinely poor (3rd percentile, a real ~1-win drag), not the asset that
        BLK% implied.
        """
    )
    return


@app.cell
def _(mo):
    mo.md(
        """
        ---
        **Caveats.** DPM uncertainty is modeled as N(dpm, 1.2) and minutes as
        lognormal (injury/role) — transparent assumptions, not DARKO's true
        posterior, so read the interval's *width* as illustrative. The fit bump
        applies a lineup-level A2 coefficient to a season aggregate at half
        strength — deliberately conservative. Pythagorean uses exponent 13.91 and
        ~115 ppg. The point isn't a precise win total; it's the method: **project a
        distribution, price moves in wins, and keep fit in proportion to talent.**
        """
    )
    return


@app.cell
def _():
    import altair as alt
    import marimo as mo
    import numpy as np
    import pandas as pd

    from _lab import TEAM_COLORS as team_colors
    from _lab import load_mart

    return alt, load_mart, mo, np, pd, team_colors


if __name__ == "__main__":
    app.run()
