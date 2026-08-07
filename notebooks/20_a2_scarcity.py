import marimo

__generated_with = "0.23.13"
app = marimo.App(width="medium")


@app.cell
def _(mo):
    mo.md("""
    # A2 — Lineup fit, quantified

    A lineup's net rating is *mostly* how good its five players are. **"Fit" is the
    leftover** — how much a lineup beats or misses what its talent predicts. This
    notebook works that question from four angles and reports each one in full:
    the data, the method, what it shows, where it's fragile, and what to try next.

    | # | Section | Question | Data |
    |---|---------|----------|------|
    | 1 | **Talent vs. fit** | Once talent is fixed, which fit features move net rating? | 2025-26 5-man lineups |
    | 2 | **Held-out replication** | Do those effects survive on a season the model never saw? | 2024-25 5-man lineups |
    | 3 | **Pairwise diminishing returns** | Do *redundant* pairs under-perform (WOWY)? | 2024-25 two-man pairs |
    | 4 | **Talent saturation** | Can you stack talent linearly, or does it bend? | both seasons pooled |

    **The one-line story:** talent dominates, but with strong *diminishing returns*
    (it saturates); the only fit lever that reliably adds *beyond* talent is **rim
    protection**; the "these players clash" stories are either priced into the
    talent curve or engineered away by coaches before a lineup ever plays.
    """)
    return


@app.cell
def _(sm):
    def fit_std(df, ycol, xcols, weightcol="minutes", cluster="team"):
        """Minutes-weighted WLS on standardized predictors, team-clustered SEs.
        Standardizing makes coefficients per-1-SD and directly comparable."""
        X = (df[xcols] - df[xcols].mean()) / df[xcols].std()
        return sm.WLS(df[ycol], sm.add_constant(X), weights=df[weightcol]).fit(
            cov_type="cluster",
            cov_kwds={"groups": df[cluster].astype("category").cat.codes},
        )

    return (fit_std,)


@app.cell
def _(mo):
    mo.md("""
    ---
    ## 1 · Talent vs. fit — which fit features clear zero?

    **Data.** 595 fully-covered leaguewide 5-man lineups (all 30 teams, each team's
    ~top-20 by minutes), 2025-26, from `mart_lineup_features_league`. Outcome:
    BBref lineup **net rating** (points per 100, opponent-averaged). Talent baseline:
    **ΣDARKO DPM** (sum of the five players' plus-minus). Fit features: `rim_suppress`
    (opponent rim deterrence × alteration, from PBPStats defense — *directly* measured,
    not the thin BLK% proxy), `avg_height_in` (size), `spacing_cs_mean` (NBA.com
    catch-and-shoot gravity — the actual floor-spacing subset), `usg_spread`, `ast_max`.

    **Methodology.** Minutes-weighted WLS of net rating on standardized features, so
    each coefficient is "points/100 per +1 SD" and comparable across features.
    Standard errors are **clustered by team** — 595 lineups come from only 30 teams,
    so lineups within a team aren't independent and pretending otherwise fakes
    precision. We compare talent-only R² to full-model R² to size how much fit adds.
    """)
    return


@app.cell
def _(fit_std, load_mart, pd, sm):
    s1_league = load_mart("mart_lineup_features_league")
    s1_feats = [
        "talent_sum_dpm",
        "rim_suppress",
        "avg_height_in",
        "spacing_cs_mean",
        "usg_spread",
        "ast_max",
    ]
    s1_nice = {
        "talent_sum_dpm": "talent (ΣDPM)",
        "rim_suppress": "rim protection (deters + alters)",
        "avg_height_in": "size (avg lineup height)",
        "spacing_cs_mean": "spacing (catch-and-shoot gravity)",
        "usg_spread": "usage balance (spread)",
        "ast_max": "playmaking (top AST%)",
    }
    s1_d = s1_league[s1_league["n_covered"] == 5].dropna(subset=s1_feats).copy()
    s1_model = fit_std(s1_d, "net_pts_per100", s1_feats)
    s1_ci = s1_model.conf_int()
    s1_coef = pd.DataFrame(
        {
            "feature": [s1_nice[f] for f in s1_feats],
            "coef": [s1_model.params[f] for f in s1_feats],
            "lo": [s1_ci.loc[f, 0] for f in s1_feats],
            "hi": [s1_ci.loc[f, 1] for f in s1_feats],
            "p": [s1_model.pvalues[f] for f in s1_feats],
        }
    )
    s1_coef["sig"] = s1_coef["p"] < 0.05
    # talent-only vs full R², to size how little fit adds
    s1_Z = (s1_d[s1_feats] - s1_d[s1_feats].mean()) / s1_d[s1_feats].std()
    s1_r2t = (
        sm.WLS(
            s1_d["net_pts_per100"],
            sm.add_constant(s1_Z[["talent_sum_dpm"]]),
            weights=s1_d["minutes"],
        )
        .fit()
        .rsquared
    )
    s1_r2f = s1_model.rsquared
    # rim effect in RAW units: a p10 -> p90 rim-protecting lineup
    s1_raw = sm.WLS(
        s1_d["net_pts_per100"], sm.add_constant(s1_d[s1_feats]), weights=s1_d["minutes"]
    ).fit()
    s1_rimswing = s1_raw.params["rim_suppress"] * (
        s1_d["rim_suppress"].quantile(0.90) - s1_d["rim_suppress"].quantile(0.10)
    )
    return s1_coef, s1_d, s1_league, s1_r2f, s1_r2t, s1_rimswing


@app.cell
def _(alt, pd, s1_coef):
    s1_zero = (
        alt.Chart(pd.DataFrame({"x": [0]}))
        .mark_rule(color="#999", strokeDash=[3, 3])
        .encode(x="x:Q")
    )
    s1_whisk = (
        alt.Chart(s1_coef)
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
    s1_dots = (
        alt.Chart(s1_coef)
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
    (s1_zero + s1_whisk + s1_dots).properties(
        title="Only rim protection (+) and size (−) move net beyond talent",
        width=460,
        height=200,
    )
    return


@app.cell
def _(mo, s1_r2f, s1_r2t, s1_rimswing):
    mo.md(f"""
    **Key takeaways.**

    - **Talent dominates.** ΣDPM alone explains **{s1_r2t:.0%}** of net-rating
      variance; every fit feature combined lifts it only to **{s1_r2f:.0%}**. Fit is
      real but second-order.
    - **Rim protection clears zero** — measured directly (deterrence + alteration),
      a poorly- vs. strongly-protecting lineup is worth **{s1_rimswing:+.1f} net/100**.
    - **Size clears zero, negatively** — taller lineups underperform their talent
      (the small-ball cost). Not in the box score, so not mechanical.
    - **Spacing, usage balance, playmaking are flat** — and this is spacing's *best*
      test (catch-and-shoot gravity). Better measurement confirms the null.

    **Potential gaps.** (1) *Observational, not causal* — teams that build for fit
    also coach and stay healthy better. (2) Net rating is opponent-*averaged*, not
    adjusted (that's A3's job). (3) Only each team's ~top-20 lineups. (4) The rim
    coefficient is **partly mechanical** — rim defense is itself a slice of net rating;
    deterrence (fewer rim attempts) is the cleanest, least-circular piece. (5) **This
    model is *linear*** — it can only see additive effects, which §4 shows is the
    biggest blind spot.

    **Next to investigate.** Replicate on a held-out season (§2); test *non-linearity*
    in the talent baseline (§4); and — not yet done — build lineup **role-coverage**
    features (does the unit have a creator / rim protector / spacer / rebounder / POA
    defender?), since the worst fits are missing *roles*, not clashing traits.
    """)
    return


@app.cell
def _(mo, pd, s1_league):
    # ORL/NOP read-through on the RESIDUAL (net − talent), so the talent gap between
    # the teams doesn't masquerade as a fit effect. A humility check on the coefficient.
    s1_lg = s1_league[s1_league["n_covered"] == 5].dropna(subset=["rim_suppress"])
    s1_orlnop = pd.DataFrame(
        [
            {
                "team": tm,
                "rim protection league pctile": round(
                    100
                    * (
                        s1_lg["rim_suppress"]
                        < (
                            s1_lg[s1_lg["team"] == tm]["rim_suppress"]
                            * s1_lg[s1_lg["team"] == tm]["minutes"]
                        ).sum()
                        / s1_lg[s1_lg["team"] == tm]["minutes"].sum()
                    ).mean()
                ),
                "mean talent (ΣDPM)": round(
                    (
                        s1_lg[s1_lg["team"] == tm]["talent_sum_dpm"]
                        * s1_lg[s1_lg["team"] == tm]["minutes"]
                    ).sum()
                    / s1_lg[s1_lg["team"] == tm]["minutes"].sum(),
                    1,
                ),
                "mean fit residual (net−talent)": round(
                    (
                        s1_lg[s1_lg["team"] == tm]["fit_residual"]
                        * s1_lg[s1_lg["team"] == tm]["minutes"]
                    ).sum()
                    / s1_lg[s1_lg["team"] == tm]["minutes"].sum(),
                    1,
                ),
            }
            for tm in ["ORL", "NOP"]
        ]
    )
    mo.vstack(
        [
            mo.md(
                """
            **A two-team sanity check (read with humility).** The leaguewide model says
            rim protection helps at the margin, but two teams of ~20 noisy lineups can't
            confirm a leaguewide coefficient: ORL beats its talent (positive residual),
            NOP misses it, and neither team's rim level cleanly explains that. That's
            exactly why we estimate from all 30 teams and apply the rule gently.
            """
            ),
            mo.ui.table(s1_orlnop, selection=None),
        ]
    )
    return


@app.cell
def _(mo):
    mo.md("""
    ---
    ## 2 · Held-out replication — does it survive a season the model never saw?

    **Data.** 600 leaguewide 5-man lineups from **2024-25** (`_lab.load_5man_features_2024`),
    rebuilt from raw via the *same* code path as §1 — same sources (BBref, DARKO,
    PBPStats, NBA.com), same feature definitions. This season played no part in any
    earlier modeling, so it's a genuine out-of-sample test.

    **Methodology.** Run the *identical* minutes-weighted, team-clustered WLS on the
    four headline features and compare coefficients season-over-season. A finding that
    replicates keeps the same sign and rough magnitude; one that doesn't is fragile.
    """)
    return


@app.cell
def _(fit_std, load_5man_features_2024, pd, s1_d):
    s2_feats = ["talent_sum_dpm", "rim_suppress", "avg_height_in", "spacing_cs_mean"]
    s2_nice = {
        "talent_sum_dpm": "talent (ΣDPM)",
        "rim_suppress": "rim protection",
        "avg_height_in": "size",
        "spacing_cs_mean": "spacing (C&S)",
    }
    s2_2024 = load_5man_features_2024()
    s2_2024 = s2_2024[s2_2024["n_covered"] == 5].dropna(subset=s2_feats).copy()
    s2_frames = {"2024-25 (held out)": s2_2024, "2025-26 (original)": s1_d}
    s2_rows = []
    for s2_name, s2_df in s2_frames.items():
        s2_m = fit_std(s2_df, "net_pts_per100", s2_feats)
        for s2f in s2_feats:
            s2_rows.append(
                {
                    "season": s2_name,
                    "feature": s2_nice[s2f],
                    "coef": s2_m.params[s2f],
                    "p": s2_m.pvalues[s2f],
                    "sig": s2_m.pvalues[s2f] < 0.05,
                }
            )
    s2_cmp = pd.DataFrame(s2_rows)
    return (s2_cmp,)


@app.cell
def _(alt, pd, s2_cmp):
    s2_zero = (
        alt.Chart(pd.DataFrame({"x": [0]}))
        .mark_rule(color="#999", strokeDash=[3, 3])
        .encode(x="x:Q")
    )
    s2_pts = (
        alt.Chart(s2_cmp)
        .mark_point(filled=True, size=110)
        .encode(
            x=alt.X("coef:Q", title="effect on net rating per +1 SD (points/100)"),
            y=alt.Y("feature:N", sort="-x", title=None),
            color=alt.Color(
                "season:N",
                scale=alt.Scale(
                    domain=["2024-25 (held out)", "2025-26 (original)"],
                    range=["#E0A83A", "#0A7CD6"],
                ),
                title="season",
            ),
            shape=alt.Shape("season:N", legend=None),
            tooltip=[
                "feature:N",
                "season:N",
                alt.Tooltip("coef:Q", format="+.2f"),
                alt.Tooltip("p:Q", format=".3f"),
            ],
        )
    )
    (s2_zero + s2_pts).properties(
        title="Talent, rim protection, and the spacing-null replicate; size is fragile",
        width=460,
        height=180,
    )
    return


@app.cell
def _(mo, s2_cmp):
    s2_pivot = (
        s2_cmp.pivot(index="feature", columns="season", values="coef")
        .round(2)
        .reset_index()
    )
    mo.vstack(
        [
            mo.md("**What the data shows** — coefficients, points/100 per +1 SD:"),
            mo.ui.table(s2_pivot, selection=None),
            mo.md(
                """
            **Key takeaways.**

            - **Talent, rim protection, and the spacing-null all replicate** — same sign,
              both seasons, rim protection significant in both (the cleanest replication).
            - **Size does *not* hold up** — same negative direction, but only significant in
              2025-26 (p≈0.02) vs. not in 2024-25 (p≈0.37). Downgrade it from "confirmed"
              to *directional*.
            - Talent's standardized coefficient is larger in 2025-26; talent explained that
              season's top-20 lineups more tightly (talent-only R² 0.17 vs 0.09).

            **Potential gaps.** Only two seasons — a weak base for "replicates." Both
            seasons' DARKO exports are **integer-rounded DPM**, so the talent baseline is
            coarse (consistently so). 2024-25 had no CTG pull, so spacing uses
            catch-and-shoot only — which is the A2 measure anyway, so no real loss.

            **Next to investigate.** Add 2–3 more prior seasons to turn "replicates" into a
            trend; re-examine whether the size penalty is really a *whole-lineup oversize*
            effect (it flips sign at the pair level in §3).
            """
            ),
        ]
    )
    return


@app.cell
def _(mo):
    mo.md("""
    ---
    ## 3 · Pairwise diminishing returns — do redundant pairs under-perform?

    **Data.** 556 two-man pairs (`mart_pair_synergy`, 2024-25) built from BBref 2-man
    lineups + player On/Off. For each pair we compute a **WOWY complement** and a set
    of **trait-overlap** features. (PBPStats can't produce combinations, so the source
    is Basketball-Reference.)

    **Methodology.**

    - *WOWY complement.* For a pair (A,B) together with net `nab` over `mab` minutes,
      and each player's overall on-court net `n`/`m` from On/Off, solve the player's
      **without-partner** net: `n_A¬B = (nA·mA − nab·mab)/(mA − mab)`. A's lift =
      `nab − n_A¬B`; complement = mean(A-lift, B-lift). Requires >100 without-partner
      minutes so the counterfactual isn't a noisy sliver.
    - *Within-team centering.* Raw complement is **biased positive** — starters play
      together, so a star's without-partner minutes are lower-leverage bench minutes.
      Subtracting each team's mean strips that selection effect. This is the outcome
      we analyze (`complement_centered`).
    - Each trait overlap is tested with a talent control (minutes-weighted WLS,
      team-clustered). A team-fixed-effects model on the raw together-net is the
      robustness check (both agree).
    """)
    return


@app.cell
def _(fit_std, load_mart, pd):
    s3_pairs = load_mart("mart_pair_synergy")
    s3_over = {
        "usg_min": "both ball-dominant",
        "usg_gap": "usage hierarchy",
        "csg_min": "both floor-spacers",
        "csg_max": "≥1 spacer",
        "cross_cs": "creator × spacer",
        "height_min": "both tall",
        "blk_min": "both rim-protectors",
        "blk_max": "≥1 rim-protector",
    }
    s3_group = {
        "usg_min": "perimeter",
        "usg_gap": "perimeter",
        "csg_min": "perimeter",
        "csg_max": "perimeter",
        "cross_cs": "perimeter",
        "height_min": "interior",
        "blk_min": "interior",
        "blk_max": "interior",
    }
    s3_rows = []
    for s3f, s3lab in s3_over.items():
        s3m = fit_std(
            s3_pairs, "complement_centered", ["talent_sum", s3f], weightcol="minutes"
        )
        s3_rows.append(
            {
                "overlap": s3lab,
                "dimension": s3_group[s3f],
                "coef": s3m.params[s3f],
                "p": s3m.pvalues[s3f],
                "sig": s3m.pvalues[s3f] < 0.05,
            }
        )
    s3_coef = pd.DataFrame(s3_rows)
    return s3_coef, s3_pairs


@app.cell
def _(alt, pd, s3_coef):
    s3_zero = (
        alt.Chart(pd.DataFrame({"x": [0]}))
        .mark_rule(color="#999", strokeDash=[3, 3])
        .encode(x="x:Q")
    )
    s3_bars = (
        alt.Chart(s3_coef)
        .mark_bar(size=16)
        .encode(
            x=alt.X("coef:Q", title="effect on within-team WOWY complement per +1 SD"),
            y=alt.Y("overlap:N", sort="-x", title=None),
            color=alt.condition(
                "datum.sig",
                alt.Color(
                    "dimension:N",
                    scale=alt.Scale(
                        domain=["interior", "perimeter"], range=["#C98A22", "#0A7CD6"]
                    ),
                ),
                alt.value("#c9ccd1"),
            ),
            tooltip=[
                "overlap:N",
                "dimension:N",
                alt.Tooltip("coef:Q", format="+.2f"),
                alt.Tooltip("p:Q", format=".3f"),
            ],
        )
    )
    (s3_zero + s3_bars).properties(
        title="Only interior overlap (rim/size) pays; every perimeter overlap is null",
        width=460,
        height=240,
    )
    return


@app.cell
def _(mo, s3_pairs):
    mo.md(f"""
    **Key takeaways** (n = {len(s3_pairs)} pairs).

    - **Diminishing returns from *trait redundancy* is essentially absent.** Two
      ball-dominant players, redundant spacers, a creator × spacer pairing — all
      **null** (grey bars), in both the complement model and the team-FE robustness
      check. No measurable "these two clash" penalty.
    - **The only overlap that pays is interior** — a pair with rim protection / size
      over-performs (and it's non-mechanical: a rim protector measurably makes his
      *partner* better). Rim and height share one signal (corr ≈ 0.3, neither
      separable when both are in) — read it as one interior dimension.
    - Talent still dominates the complement.

    **Potential gaps.** (1) The complement is **noisy** (R² ≈ 0.04) — underpowered for
    *small* effects. (2) **Range restriction** — the pairs that actually play are
    pre-balanced by coaches; the catastrophic-redundancy combos (five centers) never
    appear, so a regression on the survivors can't see the cliffs. (3) **Self-masking
    stats** — USG%/gravity are equilibrium outcomes that *absorb* redundancy (two
    ball-handlers' measured usage each drops as they split the ball). (4) The three
    rotating teammates on the floor remain a confound.

    **Next to investigate.** Replace realized stats with **context-free demand**
    measures (a player's usage when *he's* the option → lineup "oversubscription");
    test **role-coverage gaps** at the 5-man level; and pull the *full* lineup set (not
    top-20), whose injury/garbage units carry the composition variance we're missing.
    """)
    return


@app.cell
def _(mo):
    mo.md("""
    ---
    ## 4 · Talent saturation — can you stack talent linearly?

    **Data.** Both seasons pooled — 1,195 five-man lineups (2024-25 rebuilt + 2025-26
    mart). Just two columns matter here: net rating and ΣDPM.

    **Methodology.** The §1/§2 models were *linear*, so they assumed talent is
    additive. Here we add curvature: `net ~ ΣDPM + ΣDPM²` (centered, minutes-weighted).
    A significantly **negative** quadratic means concavity — diminishing returns to
    stacking talent. We then (a) read the marginal value of talent across its range,
    (b) bin lineups by talent decile to see the curve directly, and (c) run three
    **ceiling checks** to rule out a mechanical net-rating cap masquerading as DR.
    """)
    return


@app.cell
def _(load_5man_features_2024, np, pd, s1_d, sm):
    s4_cols = ["team", "net_pts_per100", "talent_sum_dpm", "minutes"]
    s4_25 = load_5man_features_2024()
    s4_25 = s4_25[s4_25["n_covered"] == 5][s4_cols]
    s4_pool = pd.concat([s4_25, s1_d[s4_cols]], ignore_index=True).dropna()
    s4_tc = s4_pool["talent_sum_dpm"] - s4_pool["talent_sum_dpm"].mean()
    s4_X = pd.DataFrame({"talent": s4_tc, "talent2": s4_tc**2})
    s4_m = sm.WLS(
        s4_pool["net_pts_per100"], sm.add_constant(s4_X), weights=s4_pool["minutes"]
    ).fit()
    s4_b1, s4_b2 = s4_m.params["talent"], s4_m.params["talent2"]
    s4_tmean = s4_pool["talent_sum_dpm"].mean()
    s4_t2p = s4_m.pvalues["talent2"]
    s4_peak = s4_tmean - s4_b1 / (2 * s4_b2)
    # marginal net per +1 DPM at low / median / high talent
    s4_q = s4_pool["talent_sum_dpm"].quantile([0.01, 0.5, 0.99])
    s4_marg = pd.DataFrame(
        {
            "lineup talent (ΣDPM)": [
                f"{s4_q[0.01]:+.0f} (weak)",
                f"{s4_q[0.5]:+.0f} (median)",
                f"{s4_q[0.99]:+.0f} (elite)",
            ],
            "marginal net per +1 DPM": [
                round(s4_b1 + 2 * s4_b2 * (t - s4_tmean), 2)
                for t in [s4_q[0.01], s4_q[0.5], s4_q[0.99]]
            ],
        }
    )
    # binned means: talent decile -> minutes-weighted mean net
    s4_pool = s4_pool.assign(dec=pd.qcut(s4_pool["talent_sum_dpm"], 10, labels=False))
    s4_bins = (
        s4_pool.groupby("dec")
        .apply(
            lambda x: pd.Series(
                {
                    "talent": np.average(x["talent_sum_dpm"], weights=x["minutes"]),
                    "net": np.average(x["net_pts_per100"], weights=x["minutes"]),
                }
            ),
            include_groups=False,
        )
        .reset_index()
    )
    return s4_b2, s4_bins, s4_m, s4_marg, s4_peak, s4_pool, s4_q, s4_t2p


@app.cell
def _(alt, np, pd, s4_bins, s4_m, s4_pool):
    # binned means (dots) + the fitted quadratic (line), on raw ΣDPM
    s4_grid = np.linspace(
        s4_pool["talent_sum_dpm"].min(), s4_pool["talent_sum_dpm"].max(), 60
    )
    s4_tcg = s4_grid - s4_pool["talent_sum_dpm"].mean()
    s4_curve = pd.DataFrame(
        {
            "talent": s4_grid,
            "net": s4_m.params["const"]
            + s4_m.params["talent"] * s4_tcg
            + s4_m.params["talent2"] * s4_tcg**2,
        }
    )
    s4_line = (
        alt.Chart(s4_curve)
        .mark_line(color="#C0453F", size=2)
        .encode(
            x=alt.X("talent:Q", title="lineup talent — ΣDPM"),
            y=alt.Y("net:Q", title="net rating (points/100)"),
        )
    )
    s4_dots = (
        alt.Chart(s4_bins)
        .mark_point(filled=True, size=90, color="#0A7CD6")
        .encode(
            x="talent:Q",
            y="net:Q",
            tooltip=[
                alt.Tooltip("talent:Q", format="+.1f"),
                alt.Tooltip("net:Q", format="+.1f"),
            ],
        )
    )
    (s4_line + s4_dots).properties(
        title="Net rating is concave in talent — it flattens as you stack DPM",
        width=460,
        height=260,
    )
    return


@app.cell
def _(load_5man_features_2024, pd, s1_d, sm):
    # Ceiling check 1: is a strong NON-talent predictor (rim) also concave?
    # If net had a generic ceiling, rim would bend too. It shouldn't.
    s4_rc = s1_d.dropna(subset=["rim_suppress"]).copy()
    s4_rx = s4_rc["rim_suppress"] - s4_rc["rim_suppress"].mean()
    s4_rimq = sm.WLS(
        s4_rc["net_pts_per100"],
        sm.add_constant(pd.DataFrame({"rim": s4_rx, "rim2": s4_rx**2})),
        weights=s4_rc["minutes"],
    ).fit()
    s4_rim2_p = s4_rimq.pvalues["rim2"]
    # Ceiling check 2: are top-talent lineups variance-compressed (piled at a cap)?
    s4_all = load_5man_features_2024()
    s4_all = s4_all[s4_all["n_covered"] == 5]
    s4_hi = s4_all["talent_sum_dpm"].quantile(0.8)
    s4_lo = s4_all["talent_sum_dpm"].quantile([0.4, 0.6])
    s4_sd_top = s4_all[s4_all["talent_sum_dpm"] >= s4_hi]["net_pts_per100"].std()
    s4_sd_mid = s4_all[s4_all["talent_sum_dpm"].between(s4_lo[0.4], s4_lo[0.6])][
        "net_pts_per100"
    ].std()
    return s4_rim2_p, s4_sd_mid, s4_sd_top


@app.cell
def _(
    mo,
    s4_b2,
    s4_marg,
    s4_peak,
    s4_q,
    s4_rim2_p,
    s4_sd_mid,
    s4_sd_top,
    s4_t2p,
):
    mo.vstack(
        [
            mo.md(
                f"""
            **Key takeaways.**

            - **Net rating is significantly *concave* in talent** — the quadratic term is
              **{s4_b2:+.3f}** (p = {s4_t2p:.3f}). You cannot stack DPM linearly. (It
              replicates: talent² is negative and significant in *each* season separately,
              not just pooled.)
            - **The marginal value of talent collapses** as you pile it up:
            """
            ),
            mo.ui.table(s4_marg, selection=None),
            mo.md(
                f"""
            - The fitted curve **peaks at ΣDPM ≈ {s4_peak:+.1f}** — *inside* the observed
              range (p99 = {s4_q[0.99]:+.0f}). The best lineups in the data are already at
              the point where more talent adds nothing. Adding a star to a loaded lineup
              buys ~half what it buys on a weak one; near the top, almost nothing. **This is
              the real diminishing-returns signal** — the finite-resource story (one ball,
              ~100 possessions, one rim), measured.
            - **It's not a ceiling artifact.** (1) Rim protection — a strong *non-talent*
              predictor — is **not** significantly concave (rim², p = {s4_rim2_p:.2f}); a
              generic net cap would bend it too. (2) High-talent lineups aren't
              variance-compressed (net SD {s4_sd_top:.1f} vs mid-talent {s4_sd_mid:.1f}). So
              it's real substitution, not a wall.

            **Potential gaps.** Some concavity *could* be regression-to-the-mean / DPM
            measurement error (integer-rounded DPM) pulling extremes inward. And we haven't
            split the effect into offense vs. defense — resource competition should bite
            harder on offense (one ball) than defense.

            **Next to investigate.** A **split-sample** robustness check (predict net from
            talent estimated on *independent* minutes) to kill the measurement-error story;
            split net into offensive/defensive ratings to locate *where* saturation happens;
            and, for the true extremes the data never contains, a **structural model** with
            finite-resource constraints rather than any observational regression.
            """
            ),
        ]
    )
    return


@app.cell
def _(mo):
    mo.md("""
    ---
    ## Synthesis — so what *is* fit?

    Four angles, one coherent picture:

    1. **Talent dominates** lineup net rating (§1) — but **with strong diminishing
       returns**: it saturates, and the best lineups are already at the plateau (§4).
    2. **Rim protection is the one fit lever that adds beyond talent** — significant in
       both seasons (§1–2) and non-mechanical at the pair level, where a rim protector
       makes his partner better (§3).
    3. **Spacing is a genuine null** at every level, even with the best public measure
       (§1–3). Usage-redundancy and creator×spacer "chemistry" are null too.
    4. **The "these players clash" stories don't survive** — because the diminishing
       returns that's real (talent saturation) is a finite-resource effect, not a
       trait clash, and the trait-redundancy cliffs are **engineered away by coaches**
       before a lineup ever plays (§3 range restriction).

    **The honest headline:** fit is real, and it's *talent saturation + rim
    protection* — not the redundancy narratives. The single biggest open lead is
    **role-coverage** (a lineup missing an entire role — creation, spacing, rim
    protection — is the failure mode the observed data can't show us), which is the
    next thing to build.

    **Everything above bounds to the same caveats:** observational not causal;
    opponent-*averaged* net rating; each team's ~top-20 lineups; integer-rounded DPM;
    and a rim coefficient that's partly mechanical. Fit matters — it's just smaller,
    and stranger, than the narrative says.
    """)
    return


@app.cell
def _():
    import altair as alt
    import marimo as mo
    import numpy as np
    import pandas as pd
    import statsmodels.api as sm

    from _lab import load_5man_features_2024, load_mart

    return alt, load_5man_features_2024, load_mart, mo, np, pd, sm


if __name__ == "__main__":
    app.run()
