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
        **What this means for the Magic & Pelicans (and the caveats).** You can
        largely ignore opponent style when projecting *outcomes* — beating a team
        is about talent and home court, not their archetype. Style matters for
        *preparation*: expect your shot diet and tempo to bend toward the
        opponent's scheme. Caveats: 171 games, one season; opponent style measured
        at the season level; the rim-protection matchup we hypothesized (rim-heavy
        offense vs rim-deterring defense) did **not** show a detectable outcome
        effect here — an honest null worth revisiting with more data.
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
    from _lab import load_mart

    return (
        KMeans,
        StandardScaler,
        adjusted_rand_score,
        alt,
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
