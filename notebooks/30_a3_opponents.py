import marimo

__generated_with = "0.23.13"
app = marimo.App(width="medium")


@app.cell
def _(mo):
    mo.md(
        """
        # A3 — Opponent style: archetypes, and does it matter?

        Two questions. First, do NBA teams sort into clean *style archetypes*
        (pace-and-space, rim-pressure, drop-coverage walls…)? Second — the one
        that matters for the Magic and Pelicans — once you know how *good* an
        opponent is, does how they *play* change anything?

        Short answers: the archetypes are **fuzzy**, and opponent style moves
        **how you play, not whether you win**.
        """
    )
    return


@app.cell
def _(load_mart):
    team_style = load_mart("mart_team_style")
    games = load_mart("mart_games_styled")
    return games, team_style


@app.cell
def _(mo):
    mo.md("## 1. Do team styles cluster? (barely)")
    return


@app.cell
def _(mo):
    k = mo.ui.slider(3, 7, value=4, label="k (clusters)")
    k
    return (k,)


@app.cell
def _(
    KMeans, StandardScaler, adjusted_rand_score, k, np, pd, silhouette_score, team_style
):
    style_feats = [
        "pace",
        "size_wavg_height_in",
        "off_rim_rate",
        "off_three_pa_rate",
        "off_long_mid_rate",
        "off_transition_rate",
        "off_orb_pct",
        "def_rim_rate_allowed",
        "def_three_pa_rate_allowed",
        "def_tov_forced_pct",
        "def_transition_rate_allowed",
    ]
    X = StandardScaler().fit_transform(team_style[style_feats])

    # scan k: silhouette (cluster separation) + stability (agreement across seeds)
    scan = []
    for kk in range(3, 8):
        sil = silhouette_score(X, KMeans(kk, n_init=10, random_state=0).fit_predict(X))
        labs = [KMeans(kk, n_init=10, random_state=s).fit_predict(X) for s in range(6)]
        ari = np.mean(
            [
                adjusted_rand_score(labs[i], labs[j])
                for i in range(6)
                for j in range(i + 1, 6)
            ]
        )
        scan.append(
            {"k": kk, "silhouette": round(sil, 3), "seed_stability_ARI": round(ari, 2)}
        )
    scan_df = pd.DataFrame(scan)

    km = KMeans(int(k.value), n_init=25, random_state=0).fit(X)
    ts = team_style.assign(cluster=km.labels_)
    z = pd.DataFrame(km.cluster_centers_, columns=style_feats)  # standardized centroids
    members = (
        ts.groupby("cluster")["team_name"]
        .apply(lambda s: ", ".join(sorted(x.split()[-1] for x in s)))
        .reset_index(name="teams")
    )
    members["defining features (|z|>0.8)"] = [
        ", ".join(
            f"{f}{'▲' if z.loc[c, f] > 0 else '▼'}"
            for f in style_feats
            if abs(z.loc[c, f]) > 0.8
        )
        for c in members["cluster"]
    ]
    return members, scan_df, style_feats


@app.cell
def _(alt, mo, scan_df):
    line = (
        alt.Chart(scan_df)
        .mark_line(point=True, color="#0A7CD6")
        .encode(
            x=alt.X("k:O", title="number of clusters (k)"),
            y=alt.Y("silhouette:Q", title="silhouette (higher = cleaner clusters)"),
        )
    )
    ref = (
        alt.Chart(alt.Data(values=[{"y": 0.25}]))
        .mark_rule(color="#c0392b", strokeDash=[4, 4])
        .encode(y="y:Q")
    )
    mo.vstack(
        [
            mo.md(
                "**Silhouette never clears ~0.12 and seed-stability tops out around"
                " 0.5** — well under the ~0.25 line where clusters start to be"
                " trustworthy. NBA team styles are a **continuum**, not clean"
                " types. (k-means needs standardized features — otherwise `pace`"
                " ~100 would swamp rates ~0.4; we scaled first.)"
            ),
            (line + ref).properties(
                width=420, height=180, title="Clusters are weak at every k"
            ),
        ]
    )
    return


@app.cell
def _(members, mo):
    mo.vstack(
        [
            mo.md(
                "**Loosely-named archetypes at the chosen k** (treat as tendencies, not types — assignments shuffle across seeds):"
            ),
            mo.ui.table(members, selection=None),
        ]
    )
    return


@app.cell
def _(mo):
    mo.md(
        """
        ## 2. Once quality is known, does opponent style matter?

        We regress our per-game numbers on the opponent's *quality* (their season
        net rating) plus their *style*, HC-robust. Style shows up in **process**,
        not **outcome**.
        """
    )
    return


@app.cell
def _(games, pd, sm):
    g = games.copy()
    g["home"] = (~g["is_away"]).astype(int)

    def fit(y, xs):
        m = sm.OLS(g[y], sm.add_constant(g[xs])).fit(cov_type="HC1")
        return m

    # PROCESS: shot-mix adaptation + pace contagion
    mix = fit(
        "three_pa_rate", ["opp_def_three_pa_rate_allowed", "opp_def_pts_poss", "home"]
    )
    pace = fit("pace", ["opp_pace", "home"])
    # OUTCOME: margin ~ quality + home + style
    style_cols = [
        "opp_off_rim_rate",
        "opp_off_three_pa_rate",
        "opp_def_tov_forced_pct",
        "opp_def_rim_rate_allowed",
    ]
    margin = fit("margin", ["opp_net_pts_poss", "home"] + style_cols)

    summary = pd.DataFrame(
        {
            "effect": [
                "PROCESS: our 3PA rate ~ opp allows 3s",
                "PROCESS: our pace ~ opp pace (contagion)",
                "OUTCOME: margin ~ opponent quality",
                "OUTCOME: margin ~ home court",
                "OUTCOME: margin ~ any opponent style",
            ],
            "coef": [
                round(mix.params["opp_def_three_pa_rate_allowed"], 3),
                round(pace.params["opp_pace"], 2),
                round(margin.params["opp_net_pts_poss"], 2),
                round(margin.params["home"], 2),
                "all n.s.",
            ],
            "p": [
                round(mix.pvalues["opp_def_three_pa_rate_allowed"], 3),
                round(pace.pvalues["opp_pace"], 3),
                round(margin.pvalues["opp_net_pts_poss"], 3),
                round(margin.pvalues["home"], 3),
                round(min(margin.pvalues[c] for c in style_cols), 3),
            ],
        }
    )
    return g, summary


@app.cell
def _(mo, summary):
    mo.vstack(
        [
            mo.md(
                "**Opponent style moves our shot selection and tempo (p<0.001), but"
                " not the scoreboard** — margin is decided by opponent quality and"
                " home court; no opponent-style feature is significant."
            ),
            mo.ui.table(summary, selection=None),
        ]
    )
    return


@app.cell
def _(alt, g, team_colors):
    # Hero chart: pace contagion — one clear, real style effect
    pts = (
        alt.Chart(g)
        .mark_circle(size=55, opacity=0.7)
        .encode(
            x=alt.X(
                "opp_pace:Q",
                title="opponent's season pace",
                scale=alt.Scale(zero=False),
            ),
            y=alt.Y("pace:Q", title="our pace this game", scale=alt.Scale(zero=False)),
            color=alt.Color(
                "team:N",
                scale=alt.Scale(
                    domain=list(team_colors.keys()), range=list(team_colors.values())
                ),
                title="team",
            ),
            tooltip=[
                "team:N",
                "opponent_abbr:N",
                alt.Tooltip("pace:Q", format=".1f"),
                alt.Tooltip("opp_pace:Q", format=".1f"),
            ],
        )
    )
    trend = pts.transform_regression("opp_pace", "pace").mark_line(color="#555")
    (pts + trend).properties(
        title="Pace is contagious: our tempo follows the opponent's",
        width=460,
        height=320,
    )
    return


@app.cell
def _(mo):
    mo.md(
        """
        ---
        ## 3. Where fit meets the standings — the swing games

        A2's verdict is that fit is *small* on the scoreboard. But games are decided
        by small margins, so even a small edge is **leveraged**. This section flags the
        **swing games**: close games (within 5 points) a team **won as an underdog** or
        **lost as a favorite**, versus what opponent quality + home court + the team's
        own baseline predicted.

        This is a *proxy* — the "surprise" in any one game is fit **plus** shooting
        variance, health, and luck. So it's a **target list of swing games**, not proof
        that fit decided them. (Turning it into a real fit-win/loss call needs per-game
        rim-protection data — the next data pull.)
        """
    )
    return


@app.cell
def _(games, np, pd, sm):
    sw_g = games.copy()
    sw_g["home"] = (~sw_g["is_away"]).astype(int)
    sw_g["nop"] = (sw_g["team"] == "NOP").astype(int)  # each team's baseline strength
    sw_X = sm.add_constant(sw_g[["opp_net_pts_poss", "home", "nop"]])
    sw_model = sm.OLS(sw_g["margin"], sw_X).fit()
    sw_g["exp_margin"] = sw_model.predict(sw_X)
    sw_g["overperf"] = sw_g["margin"] - sw_g["exp_margin"]  # game-level surprise
    sw_g["won"] = sw_g["margin"] > 0
    sw_g["close"] = sw_g["margin"].abs() <= 5

    def sw_label(r):
        if r["close"] and r["won"] and r["exp_margin"] < 0:
            return "STOLEN win"
        if r["close"] and not r["won"] and r["exp_margin"] > 0:
            return "GIFT loss"
        return ""

    sw_g["swing"] = sw_g.apply(sw_label, axis=1)
    sw_summ = pd.DataFrame(
        [
            {
                "team": t,
                "overall": f"{sw_g[sw_g.team == t].won.sum()}-{(~sw_g[sw_g.team == t].won).sum()}",
                "close games (≤5)": int(sw_g[(sw_g.team == t) & sw_g.close].shape[0]),
                "close record": f"{sw_g[(sw_g.team == t) & sw_g.close].won.sum()}-{(~sw_g[(sw_g.team == t) & sw_g.close].won).sum()}",
                "stole": int(((sw_g.team == t) & (sw_g.swing == "STOLEN win")).sum()),
                "gave away": int(
                    ((sw_g.team == t) & (sw_g.swing == "GIFT loss")).sum()
                ),
            }
            for t in ["ORL", "NOP"]
        ]
    )
    sw_log = sw_g[sw_g["swing"] != ""].copy()
    sw_log["game"] = (
        np.where(sw_log["home"] == 1, "vs ", "@ ") + sw_log["opponent_abbr"]
    )
    sw_log = (
        sw_log[
            ["team", "game_date", "game", "margin", "exp_margin", "overperf", "swing"]
        ]
        .round({"exp_margin": 1, "overperf": 1})
        .sort_values(["team", "overperf"], ascending=[True, False])
    )
    sw_log.columns = ["team", "date", "game", "actual", "expected", "surprise", "label"]
    return sw_log, sw_model, sw_summ


@app.cell
def _(mo, sw_model, sw_summ):
    mo.vstack(
        [
            mo.md(
                f"Expected margin = opponent quality + home court "
                f"(worth {sw_model.params['home']:+.1f} points) + each team's own baseline. "
                f'**"Surprise" = actual − expected.**'
            ),
            mo.ui.table(sw_summ, selection=None),
            mo.md("""
        **Orlando won its coin-flips (close record above .500); New Orleans lost
        them.** That's the swing story — and it matches A4's season read: Orlando
        *over*-shot its ~44-win projection, New Orleans *under*-shot its ~28.

        > 🏀 One honest caveat: a bad team is rarely *favored*, so it gets few
        > give-away chances — read the **close record**, not the raw stole/gave counts.
        """),
        ]
    )
    return


@app.cell
def _(mo, sw_log):
    mo.vstack(
        [
            mo.md(
                "**The swing games** — close ones won as an underdog (STOLEN) or lost "
                "as a favorite (GIFT), sorted by how surprising the result was:"
            ),
            mo.ui.table(sw_log, selection=None),
        ]
    )
    return


@app.cell
def _(games, load_games_rim, pd, sm):
    # Per-game test: does a night's rim play predict OVERPERFORMING expectation?
    rr = games.copy()
    rr["home"] = (~rr["is_away"]).astype(int)
    rr["nop"] = (rr["team"] == "NOP").astype(int)
    rr_x = sm.add_constant(rr[["opp_net_pts_poss", "home", "nop"]])
    rr["overperf"] = rr["margin"] - sm.OLS(rr["margin"], rr_x).fit().predict(rr_x)
    rr["won"] = rr["margin"] > 0
    rr["close"] = rr["margin"].abs() <= 5
    rr["date"] = rr["game_date"].astype(str)
    rr = rr.merge(load_games_rim(), on=["team", "date"], how="inner")
    rr["rim_edge"] = rr["rim_suppress_game"] - rr.groupby("team")[
        "rim_suppress_game"
    ].transform("mean")
    rr["battle_edge"] = (
        rr["own_rim"] + rr["rim_suppress_game"]
    )  # our rim scoring − theirs
    rr["battle_edge"] = rr["battle_edge"] - rr.groupby("team")["battle_edge"].transform(
        "mean"
    )

    def coefp(col):
        z = sm.add_constant(
            pd.DataFrame(
                {
                    col: (rr[col] - rr[col].mean()) / rr[col].std(),
                    "nop": (rr["team"] == "NOP").astype(int),
                }
            )
        )
        m = sm.OLS(rr["overperf"], z).fit(cov_type="HC1")
        return m.params[col], m.pvalues[col]

    rim_prot = coefp("rim_edge")
    rim_batt = coefp("battle_edge")
    rr_cg = rr[rr["close"]]
    rr_hi, rr_lo = rr_cg[rr_cg["rim_edge"] > 0], rr_cg[rr_cg["rim_edge"] < 0]
    rim_close = {
        "hi": f"{rr_hi.won.sum()}-{(~rr_hi.won).sum()}",
        "hi_pct": rr_hi.won.mean(),
        "lo": f"{rr_lo.won.sum()}-{(~rr_lo.won).sum()}",
        "lo_pct": rr_lo.won.mean(),
    }
    return rim_batt, rim_close, rim_prot


@app.cell
def _(mo, rim_batt, rim_close, rim_prot):
    mo.md(f"""
    ---
    ## 3½. Did the swing games actually track rim protection?

    We pulled **per-game** rim data (PBPStats opponent + team shot-distribution logs)
    and asked the direct question: does a night's rim play predict *overperforming*
    expectation — i.e., does **fit** (rim protection, A2's one lever) really swing games?
    `rim protection = −(opponent rim frequency × rim accuracy)`, measured against each
    team's own season norm.

    | per-game edge | effect on the "surprise" | verdict |
    |---|---|---|
    | **rim protection** (defense — *the fit lever*) | {rim_prot[0]:+.2f} pts/game | **not significant** (p = {rim_prot[1]:.2f}) |
    | full **rim battle** (offense + defense at the rim) | {rim_batt[0]:+.2f} pts/game | significant (p = {rim_batt[1]:.3f}) — but *mechanical* |

    Close games (≤5 pts): won **{rim_close["hi_pct"]:.0%}** ({rim_close["hi"]}) on
    above-norm rim-protection nights vs **{rim_close["lo_pct"]:.0%}** ({rim_close["lo"]}) below.

    > 🏀 **The honest answer.** Rim *protection* — the actual fit lever — **does not
    > reliably decide individual games** (p = {rim_prot[1]:.2f}); the swing games are mostly
    > variance. The full rim *battle* tracks the scoreboard, but that's **mechanical**
    > (scoring at the rim *is* scoring — near-circular with the margin). A ~1-win-per-season
    > fit edge is ~0.1 points a night, invisible against the ±15-point noise of one game.
    > **Fit's leverage is a faint aggregate tilt (the {rim_close["hi_pct"]:.0%}-vs-{rim_close["lo_pct"]:.0%}
    > close-game lean), not a game-by-game switch** — exactly what "fit is real but small" predicts.
    """)
    return


@app.cell
def _(mo):
    mo.md(
        """
        ---
        **What this means for the Magic & Pelicans (and the caveats).** You can largely
        ignore opponent style when projecting *outcomes* — beating a team is about talent
        and home court, not their archetype. Style matters for *preparation*: expect your
        shot diet and tempo to bend toward the opponent's scheme. The **swing games** are
        where the season turned (Orlando banked its close ones, New Orleans didn't) — but
        §3½ shows that's **not** the fit lever doing clutch work; it's mostly variance.

        *Caveats:* 171 games, one season; opponent style measured at the season level; and
        the game-level fit signal is real but too small to detect against single-game noise
        — fit shows up in the aggregate, not on any one night.
        """
    )
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

    from _lab import TEAM_COLORS as team_colors
    from _lab import load_games_rim, load_mart

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
        silhouette_score,
        sm,
        team_colors,
    )


if __name__ == "__main__":
    app.run()
