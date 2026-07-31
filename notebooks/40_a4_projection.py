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
    # A2 rim-protection coefficient (raw, per BLK%) — see notebooks/20_a2_scarcity.
    # It's the fit effect BEYOND talent, so we apply it CONSERVATIVELY (half) on
    # top of the DPM projection, which already captures most of a team's defense.
    RIM_COEF, CONSERV = 1.02, 0.5

    # team rim-protection level (minutes-weighted max BLK% across the team's
    # lineups) and the league average, from the A2 league mart.
    lu = lineups.copy()
    tr = lu.groupby("team").apply(
        lambda x: (x["rim_max_blk"] * x["minutes"]).sum() / x["minutes"].sum(),
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
        -2, 2, value=0, step=0.5, label="roster move: Δ team rim protection (BLK%)"
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
    move_net = (
        talent_delta.value + RIM_COEF * CONSERV * rim_delta.value
    )  # user's roster move
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
    # two-lever sensitivity: wins per +1 unit of each lever
    dwin_talent = pyth_wins(proj_net + 1) - pyth_wins(proj_net)
    dwin_rim = pyth_wins(proj_net + RIM_COEF * CONSERV) - pyth_wins(proj_net)
    return (
        base_net,
        dwin_rim,
        dwin_talent,
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
def _(dwin_rim, dwin_talent, fit_net, mo, team):
    mo.md(
        f"""
        ### Pricing a roster move

        - a **+1 net-rating** talent upgrade ≈ **{dwin_talent:.1f} wins**
        - a **+1 BLK%** swing in team rim protection ≈ **{dwin_rim:.1f} wins** — but
          +1 BLK% is a *large* move (roughly a league quartile), so this is fit at
          full stretch, applied conservatively.

        And {team.value}'s *actual* fit adjustment is only **{fit_net:+.1f} net**
        (well under a win) — its rim protection sits near league average. So,
        consistent with A2: fit is real and worth pricing, but **talent is what
        sets the projection** — the ORL↔NOP gap of ~16 wins is essentially all
        talent, not fit. Slide the two levers to price any move in wins.
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
