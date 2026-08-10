import marimo

__generated_with = "0.23.13"
app = marimo.App(width="medium")


@app.cell
def _(mo):
    mo.md("""
    # NBA Fit Lab — standalone: *Know your enemy* (opponent style & matchups)

    This is the **opponent-style / matchup** analysis, kept as a standalone piece (it was moved
    out of the main five-post series, where Post 3 now covers *why Orlando survived and New
    Orleans collapsed*). The finding is one-season ORL/NOP and deliberately hedged: opponent
    **style clearly changes how a game is played** (shot mix, pace), but after opponent
    **quality** and **home court** we do not detect much additional **outcome** signal. A
    stronger future version would use leaguewide games across multiple seasons with team ×
    opponent-style interactions.
    """)
    return


@app.cell
def _(mo):
    mo.md("""
    ---
    ## *Know your enemy* — opponent style, process, and outcomes

    **The question.** Do certain opponents give a team trouble *stylistically* — and when
    a team wins or loses a close game, is "fit" (rim protection) doing the deciding?

    **The data.** All of Orlando's and New Orleans's games (`mart_games_styled`: margin,
    opponent quality, home/away, opponent style), plus **per-game** rim data
    (`load_games_rim`, from PBPStats).

    **The method.** First, do teams even cluster into clean style archetypes? Then a
    process-vs-outcome regression (does opponent style change *how* we play or *whether*
    we win?). Then a swing-game proxy, resolved with the per-game rim data.
    """)
    return


@app.cell
def _(
    KMeans, StandardScaler, adjusted_rand_score, load_mart, mo, np, pd, silhouette_score
):
    p3_ts = load_mart("mart_team_style")
    p3_sf = [
        "pace",
        "size_wavg_height_in",
        "off_rim_rate",
        "off_three_pa_rate",
        "off_transition_rate",
        "off_orb_pct",
        "def_rim_rate_allowed",
        "def_three_pa_rate_allowed",
        "def_tov_forced_pct",
    ]
    p3_x = StandardScaler().fit_transform(p3_ts[p3_sf])
    p3_scan = []
    for kk in range(3, 8):
        sil = silhouette_score(
            p3_x, KMeans(kk, n_init=10, random_state=0).fit_predict(p3_x)
        )
        labs = [
            KMeans(kk, n_init=10, random_state=s).fit_predict(p3_x) for s in range(6)
        ]
        ari = np.mean(
            [
                adjusted_rand_score(labs[i], labs[j])
                for i in range(6)
                for j in range(i + 1, 6)
            ]
        )
        p3_scan.append(
            {
                "# style groups (k)": kk,
                "how clean (silhouette)": round(sil, 3),
                "how stable (ARI)": round(ari, 2),
            }
        )
    mo.vstack(
        [
            mo.ui.table(pd.DataFrame(p3_scan), selection=None),
            mo.md("""
        Two plain scores: **how clean** (silhouette — are the groups separated? >0.25 is
        trustworthy) and **how stable** (ARI, the Adjusted Rand Index — re-run and do you
        get the same groups? 1 = identical, 0 = random). Both are low. **NBA "team types"
        are a spectrum, not boxes** — so we measure opponent style as raw numbers instead.
        """),
        ]
    )
    return


@app.cell
def _(load_mart, mo, pd, sm):
    p3_g = load_mart("mart_games_styled").copy()
    p3_g["home"] = (~p3_g["is_away"]).astype(int)

    def p3_fit(y, xs):
        return sm.OLS(p3_g[y], sm.add_constant(p3_g[xs])).fit(cov_type="HC1")

    p3_mix = p3_fit(
        "three_pa_rate", ["opp_def_three_pa_rate_allowed", "opp_def_pts_poss", "home"]
    )
    p3_pace = p3_fit("pace", ["opp_pace", "home"])
    p3_style = [
        "opp_off_rim_rate",
        "opp_off_three_pa_rate",
        "opp_def_tov_forced_pct",
        "opp_def_rim_rate_allowed",
    ]
    p3_mrg = p3_fit("margin", ["opp_net_pts_poss", "home"] + p3_style)
    p3_tab = pd.DataFrame(
        {
            "does the opponent's…": [
                "style (allows 3s)",
                "style (pace)",
                "quality",
                "home court",
                "any style trait",
            ],
            "…change our…": [
                "3-point rate",
                "pace",
                "final margin",
                "final margin",
                "final margin",
            ],
            "verdict": [
                "changes HOW we play ✓",
                "changes HOW we play ✓",
                "changes WHO wins ✓",
                "changes WHO wins ✓",
                "no effect on winning ✗",
            ],
            "p": [
                round(p3_mix.pvalues["opp_def_three_pa_rate_allowed"], 3),
                round(p3_pace.pvalues["opp_pace"], 3),
                round(p3_mrg.pvalues["opp_net_pts_poss"], 3),
                round(p3_mrg.pvalues["home"], 3),
                round(min(p3_mrg.pvalues[c] for c in p3_style), 3),
            ],
        }
    )
    mo.vstack(
        [
            mo.md(
                "**Process vs. outcome — does opponent style change how we play, or whether we win?**"
            ),
            mo.ui.table(p3_tab, selection=None),
            mo.md("""
        > 🏀 Style looks more like **preparation than prediction.** The same trait ("they allow
        > threes") raises our 3-point rate but, *in this one-season ORL/NOP sample*, doesn't
        > move the final margin once we account for opponent **quality** and **home court**
        > (~+4 points). We don't detect an outcome edge from matchup style here — which is not
        > the same as proving there is none; a leaguewide, multi-season test with style
        > interactions could still find one.
        """),
        ]
    )
    return


@app.cell
def _(load_games_rim, load_mart, mo, pd, sm):
    # Swing games + did they trace to rim protection?
    p3_rr = load_mart("mart_games_styled").copy()
    p3_rr["home"] = (~p3_rr["is_away"]).astype(int)
    p3_rr["nop"] = (p3_rr["team"] == "NOP").astype(int)
    p3_x2 = sm.add_constant(p3_rr[["opp_net_pts_poss", "home", "nop"]])
    p3_rr["overperf"] = p3_rr["margin"] - sm.OLS(p3_rr["margin"], p3_x2).fit().predict(
        p3_x2
    )
    p3_rr["won"] = p3_rr["margin"] > 0
    p3_rr["close"] = p3_rr["margin"].abs() <= 5
    p3_rr["date"] = p3_rr["game_date"].astype(str)
    p3_close = pd.DataFrame(
        [
            {
                "team": t,
                "overall": f"{p3_rr[p3_rr.team == t].won.sum()}-{(~p3_rr[p3_rr.team == t].won).sum()}",
                "close record (≤5)": f"{p3_rr[(p3_rr.team == t) & p3_rr.close].won.sum()}-{(~p3_rr[(p3_rr.team == t) & p3_rr.close].won).sum()}",
            }
            for t in ["ORL", "NOP"]
        ]
    )

    p3_j = p3_rr.merge(load_games_rim(), on=["team", "date"], how="inner")
    p3_j["rim_edge"] = p3_j["rim_suppress_game"] - p3_j.groupby("team")[
        "rim_suppress_game"
    ].transform("mean")

    def p3_coefp(col):
        z = sm.add_constant(
            pd.DataFrame(
                {
                    col: (p3_j[col] - p3_j[col].mean()) / p3_j[col].std(),
                    "nop": (p3_j["team"] == "NOP").astype(int),
                }
            )
        )
        m = sm.OLS(p3_j["overperf"], z).fit(cov_type="HC1")
        return m.params[col], m.pvalues[col]

    p3_prot = p3_coefp("rim_edge")
    return p3_close, p3_prot


@app.cell
def _(mo, p3_close, p3_prot):
    mo.vstack(
        [
            mo.md("**The swing games — who won the coin-flips?**"),
            mo.ui.table(p3_close, selection=None),
            mo.md(f"""
        Orlando won its close games; New Orleans lost them — and that matches the season
        (Orlando over-shot its win projection, New Orleans under-shot). But did *fit* do
        it? We joined **per-game rim protection** and asked whether a strong-rim night
        predicts overperforming expectation: **it doesn't** (rim-protection edge
        {p3_prot[0]:+.2f} pts/game, p = {p3_prot[1]:.2f}).

        > 🏀 Rim protection — the one fit lever — **doesn't reliably decide individual
        > games.** A ~1-win-per-season edge is ~0.1 points a night, invisible against the
        > ±15-point noise of one game. The swing games are mostly variance; fit's leverage
        > is a faint **aggregate** tilt, not a game-by-game switch.
        """),
        ]
    )
    return


@app.cell
def _(mo):
    mo.md("""
    **The takeaways.**

    > 🏀 You can ignore opponent *style* when projecting outcomes — quality and home court
    > decide games. Close games are where the season turns, but they're driven by variance,
    > not by a measurable fit edge.

    **The gaps.** 171 games, one season; opponent style measured at the season level; and
    the game-level fit signal is real but too small to see against single-game noise — fit
    shows up only in the aggregate.
    """)
    return


@app.cell
def _():
    import altair as alt
    import marimo as mo
    import numpy as np
    import pandas as pd
    import statsmodels.api as sm
    from sklearn.cluster import KMeans
    from sklearn.metrics import adjusted_rand_score, silhouette_score
    from sklearn.preprocessing import StandardScaler

    from _lab import load_games_rim, load_mart, q

    return (
        KMeans,
        StandardScaler,
        adjusted_rand_score,
        alt,
        load_games_rim,
        load_mart,
        mo,
        np,
        pd,
        q,
        silhouette_score,
        sm,
    )


if __name__ == "__main__":
    app.run()
