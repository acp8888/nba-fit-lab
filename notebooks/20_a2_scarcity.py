import marimo

__generated_with = "0.23.13"
app = marimo.App(width="medium")


@app.cell
def _(mo):
    mo.md(
        """
        # A2 — What is lineup fit worth, on top of talent?

        A lineup's net rating is *mostly* how good its five players are. "Fit" is
        the leftover — how much a lineup beats or misses what its talent predicts.
        So we take the leaguewide sample (600 lineups, all 30 teams), use **ΣDARKO
        DPM** as the talent baseline, and ask a minutes-weighted regression: once
        talent is held fixed, do continuous fit features move net rating?

        Standard errors are **clustered by team** — 600 lineups come from only 30
        teams, so lineups within a team aren't independent, and pretending they are
        would fake precision.
        """
    )
    return


@app.cell
def _(load_mart):
    league = load_mart("mart_lineup_features_league")
    return (league,)


@app.cell
def _(mo):
    min_min = mo.ui.slider(0, 150, value=0, step=10, label="min lineup minutes")
    min_min
    return (min_min,)


@app.cell
def _(league, min_min, np, pd, sm):
    # fully-covered lineups, above the minutes filter
    d = league[(league["n_covered"] == 5) & (league["minutes"] >= min_min.value)].copy()

    feats = ["talent_sum_dpm", "rim_max_blk", "spacing_min", "usg_spread", "ast_max"]
    nice = {
        "talent_sum_dpm": "talent (ΣDPM)",
        "rim_max_blk": "rim protection (max BLK%)",
        "spacing_min": "spacing (weakest 3PA rate)",
        "usg_spread": "usage balance (spread)",
        "ast_max": "playmaking (top AST%)",
    }
    # standardize predictors -> coefficients are per-1-SD and comparable
    Z = (d[feats] - d[feats].mean()) / d[feats].std()
    model = sm.WLS(d["net_pts_per100"], sm.add_constant(Z), weights=d["minutes"]).fit(
        cov_type="cluster", cov_kwds={"groups": d["team"].astype("category").cat.codes}
    )
    ci = model.conf_int()
    coef = pd.DataFrame(
        {
            "feature": [nice[f] for f in feats],
            "coef": [model.params[f] for f in feats],
            "lo": [ci.loc[f, 0] for f in feats],
            "hi": [ci.loc[f, 1] for f in feats],
            "p": [model.pvalues[f] for f in feats],
        }
    )
    coef["sig"] = coef["p"] < 0.05

    # talent-only vs +fit, to show how little fit adds
    r2_talent = (
        sm.WLS(
            d["net_pts_per100"],
            sm.add_constant(Z[["talent_sum_dpm"]]),
            weights=d["minutes"],
        )
        .fit()
        .rsquared
    )
    r2_full = (
        sm.WLS(d["net_pts_per100"], sm.add_constant(Z), weights=d["minutes"])
        .fit()
        .rsquared
    )

    # rim effect in raw units: weak (p25) -> strong (p90) shot-blocker
    raw = sm.WLS(
        d["net_pts_per100"], sm.add_constant(d[feats]), weights=d["minutes"]
    ).fit()
    lo_b, hi_b = d["rim_max_blk"].quantile(0.25), d["rim_max_blk"].quantile(0.90)
    rim_swing = raw.params["rim_max_blk"] * (hi_b - lo_b)
    return coef, d, r2_full, r2_talent, rim_swing


@app.cell
def _(alt, coef, pd):
    # Hero chart: standardized coefficient plot (one claim — which fit feature clears zero)
    zero = (
        alt.Chart(pd.DataFrame({"x": [0]}))
        .mark_rule(color="#999", strokeDash=[3, 3])
        .encode(x="x:Q")
    )
    whisk = (
        alt.Chart(coef)
        .mark_rule(size=2)
        .encode(
            x=alt.X("lo:Q", title="effect on net rating per +1 SD (points/100)"),
            x2="hi:Q",
            y=alt.Y("feature:N", sort="-x", title=None),
            color=alt.condition(
                "datum.sig", alt.value("#0A7CD6"), alt.value("#9aa0a6")
            ),
        )
    )
    dots = (
        alt.Chart(coef)
        .mark_point(filled=True, size=90)
        .encode(
            x="coef:Q",
            y=alt.Y("feature:N", sort="-x"),
            color=alt.condition(
                "datum.sig", alt.value("#0A7CD6"), alt.value("#9aa0a6")
            ),
            tooltip=[
                alt.Tooltip("feature:N"),
                alt.Tooltip("coef:Q", format="+.2f"),
                alt.Tooltip("lo:Q", format="+.2f"),
                alt.Tooltip("hi:Q", format="+.2f"),
                alt.Tooltip("p:Q", format=".3f"),
            ],
        )
    )
    (zero + whisk + dots).properties(
        title="Rim protection is the only fit feature that clears zero (talent-controlled)",
        width=460,
        height=200,
    )
    return


@app.cell
def _(mo, r2_full, r2_talent, rim_swing):
    mo.md(
        f"""
        ### The finding

        - **Talent dominates.** ΣDPM alone explains **{r2_talent:.0%}** of lineup
          net-rating variance; adding every fit feature lifts it only to
          **{r2_full:.0%}**. Fit is a real but second-order effect.
        - **Rim protection is the one fit dimension that clears zero** after
          controlling for talent — and it's *beyond* each player's own DPM, the
          hallmark of complementarity: a rim protector anchors a lineup for more
          than his individual value. Going from a weak (p25) to a strong (p90)
          shot-blocker is worth **{rim_swing:+.1f} net/100**.
        - **Spacing, usage balance, and playmaking do not show a robust
          independent effect** here — notably counter to the "spacing is
          everything" narrative. (Caveat: spacing is proxied by 3PA *rate* only;
          a willingness×accuracy version is the next refinement.)
        """
    )
    return


@app.cell
def _(league, mo, pd):
    # ORL/NOP read-through — on the RESIDUAL (net - talent), not raw net, so the
    # talent gap between the teams doesn't masquerade as a fit effect.
    lg = league[league["n_covered"] == 5]

    def wmean(t, col):
        return (t[col] * t["minutes"]).sum() / t["minutes"].sum()

    rows = []
    for tm in ["ORL", "NOP"]:
        t = lg[lg["team"] == tm]
        rows.append(
            {
                "team": tm,
                "rim (max BLK%) league pctile": round(
                    100 * (lg["rim_max_blk"] < t["rim_max_blk"].mean()).mean()
                ),
                "mean talent (ΣDPM)": round(wmean(t, "talent_sum_dpm"), 1),
                "mean fit residual (net−talent)": round(wmean(t, "fit_residual"), 1),
            }
        )
    mo.vstack(
        [
            mo.md(
                """
                **Reading the Magic & Pelicans — with humility.** The leaguewide
                model says rim protection helps at the margin. These two teams
                *don't* individually confirm it: **ORL beats its talent by ~+5/100
                with below-median rim protection**, while **NOP misses by ~−1 with
                top-quartile rim protection.** Twenty noisy lineups per team can't
                be explained by one coefficient — which is exactly why we estimate
                the rule from all 30 teams and apply it gently, instead of reading
                two teams' residuals as truth.
                """
            ),
            mo.ui.table(pd.DataFrame(rows), selection=None),
        ]
    )
    return


@app.cell
def _(mo):
    mo.md(
        """
        ---
        **Caveats (these bound every claim above).** Observational, not causal —
        teams that build for fit also tend to coach and stay healthy better.
        Net rating is opponent-*averaged*, not opponent-*adjusted* (that's A3's
        job, at the team level). These are each team's ~top-20 most-used lineups,
        not all lineups. Rim protection is proxied by BLK% alone. And "fit adds
        ~2% of variance" means: real at the margins, dwarfed by talent — which is
        itself the honest headline for Post 2.
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

    from _lab import load_mart

    return alt, load_mart, mo, np, pd, sm


if __name__ == "__main__":
    app.run()
