import marimo

__generated_with = "0.23.13"
app = marimo.App(width="medium")


@app.cell
def _(mo):
    mo.md("""
    # NBA Fit Lab — the whole series, one notebook

    A guided walk through every planned blog post. Each section answers the same five
    questions in plain English: **what are we asking, what data, what method, what did
    we find, and where is it fragile.** Every number is computed live from the real data.

    | Post | Title | The fan question |
    |---|---|---|
    | **1** | *What do you build around a non-shooting star?* | Orlando duplicated its star's flaw; New Orleans complemented it — did either work? |
    | **2** | *Fit, quantified* | Do the right pieces around a star add wins — or is it just talent? |
    | **3** | *Know your enemy* | Do matchups decide games — and do close games trace to "fit"? |
    | **4** | *The moves that matter* | How many wins is this roster, and what move helps most? |
    | **5** | *Same coach, new roster* | Are the predictions coming true? (in-season) |

    > 🏀 **The one-sentence story:** talent decides almost everything — but it
    > **saturates** (each added star helps less), and the only "fit" that reliably helps
    > on top of talent is **rim protection**. Spacing and "these two can't play together"
    > mostly vanish once you account for how good the players already are.
    """)
    return


@app.cell
def _(mo):
    mo.md("""
    ### The words we use (glossary)

    | Term | Plain meaning |
    |---|---|
    | **Net rating** | How much a lineup/team outscores opponents by **per 100 possessions**. +5 good, −5 bad, ±10 extreme. |
    | **DPM** (Daily Plus-Minus) | One number for how much a **single player** helps per 100 possessions (public **DARKO** model). Our talent yardstick. |
    | **ΣDPM** | The five players' DPM **added up** — the net rating the *sum of the parts* predicts. |
    | **Fit** | Performance **beyond** talent: `net − ΣDPM`. Positive = the group beat its parts. |
    | **Rim protection** | How well a lineup stops opponents at the rim (scaring them off *and* making them miss). |
    | **Spacing / gravity** | How much a shooter pulls defenders out to the arc. Measured from **catch-and-shoot** threes. |
    | **WOWY** (With Or Without You) | A player's team results **with him on vs. off** the floor. |
    | **Diminishing returns** | Each added star helps **less** — one ball, ~100 possessions, one rim to share. |
    | Sources | **BBref** (Basketball-Reference), **PBPStats**, **DARKO**, **CTG** (Cleaning the Glass). |

    *Method footnotes use **WLS** (a regression that trusts big-minute lineups more),
    **R²** (share of the ups-and-downs explained), and **p-value** (< 0.05 = "probably
    real, not luck"). The takeaways stand on their own without them.*
    """)
    return


@app.cell
def _(pd, sm):
    def fit_std(df, ycol, xcols, weightcol="minutes", cluster="team"):
        """Minutes-weighted WLS on standardized predictors, team-clustered errors —
        so coefficients are per-1-SD and comparable, and errors don't fake precision."""
        x = (df[xcols] - df[xcols].mean()) / df[xcols].std()
        return sm.WLS(df[ycol], sm.add_constant(x), weights=df[weightcol]).fit(
            cov_type="cluster",
            cov_kwds={"groups": df[cluster].astype("category").cat.codes},
        )

    return (fit_std,)


# ============================ POST 1 =========================================
@app.cell
def _(mo):
    mo.md("""
    ---
    # Post 1 · *When your best player can't shoot, what do you build around him?*

    **The question.** Orlando and New Orleans are built around the *same* kind of star — a
    ball-dominant, high-usage forward who lives at the rim and doesn't space the floor
    (Banchero, Williamson). They made **opposite bets** on what to surround him with.
    Orlando **duplicated** the archetype; New Orleans **complemented** it. Did either work?

    **The data.** `mart_player_league` — every rotation player's traits as **league
    percentiles**, both seasons (usage, 3-point rate, catch-&-shoot spacing, assist rate,
    efficiency), built from public BBref + NBA.com + DARKO.

    **The method.** Compare the two stars' percentile fingerprints (are they really the
    same archetype?), then their supporting casts. One chart on the two axes that define
    the archetype — usage (ball-dominance) vs. catch-&-shoot spacing — shows who *copied*
    the star and who *offset* him. We do **not** assume the inversion holds; we check it.
    """)
    return


@app.cell
def _(load_mart, pd):
    p1_pl = load_mart("mart_player_league")
    p1_cur = p1_pl[
        (p1_pl["season"] == 2026) & (p1_pl["team"].isin(["ORL", "NOP"]))
    ].copy()
    p1_key = {
        "Paolo Banchero": "Banchero ★",
        "Franz Wagner": "Wagner",
        "Wendell Carter Jr.": "Carter",
        "Goga Bitadze": "Bitadze",
        "Zion Williamson": "Williamson ★",
        "Trey Murphy III": "Murphy",
        "Yves Missi": "Missi",
        "Derik Queen": "Queen",
    }
    p1_cur["label"] = p1_cur["player_name"].map(p1_key)
    p1_fp = (
        p1_cur[p1_cur["player_name"].isin(p1_key)][
            [
                "team",
                "player_name",
                "usg_pctl",
                "tpar_pctl",
                "csg_pctl",
                "ast_pctl",
                "ts_pctl",
            ]
        ]
        .rename(
            columns={
                "usg_pctl": "usage",
                "tpar_pctl": "3PA rate",
                "csg_pctl": "C&S spacing",
                "ast_pctl": "assist",
                "ts_pctl": "efficiency",
            }
        )
        .sort_values(["team", "usage"], ascending=[True, False])
    )
    return p1_cur, p1_fp


@app.cell
def _(alt, p1_cur):
    p1_enc = alt.Chart(p1_cur).encode(
        x=alt.X("usg_pctl:Q", title="usage percentile  (ball-dominance →)"),
        y=alt.Y(
            "csg_pctl:Q", title="catch-&-shoot spacing percentile  (floor-spacing →)"
        ),
    )
    p1_dots = p1_enc.mark_circle(size=90, opacity=0.55).encode(
        color=alt.Color(
            "team:N",
            scale=alt.Scale(domain=["ORL", "NOP"], range=["#0A7CD6", "#E03A3E"]),
            title="team",
        ),
        tooltip=["player_name", "team", "usg_pctl", "csg_pctl"],
    )
    p1_txt = (
        alt.Chart(p1_cur.dropna(subset=["label"]))
        .mark_text(align="left", dx=7, fontSize=11)
        .encode(x="usg_pctl:Q", y="csg_pctl:Q", text="label:N", color=alt.value("#444"))
    )
    (p1_dots + p1_txt).properties(
        title="Same star archetype (bottom-right), opposite bets around it",
        width=480,
        height=340,
    )
    return


@app.cell
def _(mo, p1_fp):
    mo.vstack(
        [
            mo.md("**The fingerprints — league percentiles, 2025-26** (★ = the star):"),
            mo.ui.table(p1_fp, selection=None),
            mo.md("""
        - **The stars match.** Banchero and Williamson are both elite-usage (85–91st),
          bottom-quintile 3-point volume, high-assist — ball-dominant non-shooting forwards.
        - **The bets invert — at the wing.** Orlando's Wagner is a near-copy of Banchero
          (89th usage, 21st 3PA rate, 33rd spacing) → a **duplicate**. New Orleans's Murphy
          is the opposite (74th 3PA rate, **82nd spacing**) → a **complement**.
        - **But it breaks at center.** Both teams run non-shooting bigs (Carter/Bitadze,
          Missi), and New Orleans's Queen is *himself* a high-usage non-shooter (66th usage,
          11th 3PA) — a second duplicate. New Orleans only *half*-complemented.
        """),
        ]
    )
    return


@app.cell
def _(mo):
    mo.md("""
    **The takeaways.**

    > 🏀 Same kind of star (a ball-dominant forward who can't shoot), two opposite bets:
    > Orlando **doubled down** (a second non-shooting creator), New Orleans **added a spacer**
    > (Murphy) — then duplicated at center. **Both bets underachieved** (Orlando 45-37 and out
    > in seven; New Orleans 26-56). That's the hook: *if adding spacing also failed, spacing
    > was never the answer* — which is exactly what Post 2 tests.

    **The gaps.** The archetype is drawn from public percentiles — no leaguewide **rim
    frequency** yet, so "lives at the rim" leans on ORL/NOP-only detail. It's **n=2** (the
    leaguewide version — every team built around a ball-dominant non-shooter — is the next
    build). And the pairwise "duplicate hurts" claim is a **2024-25** result (Post 2), a
    different season than these 2025-26 fingerprints.
    """)
    return


@app.cell
def _(mo):
    mo.md("""
    ---
    ### Does the inversion generalize? (beyond n=2)

    Two teams is an anecdote. Using the leaguewide flags, we take **every** team built around
    a ball-dominant non-shooter (its top-usage player is one), classify what it built around
    him — **duplicate** (a second such star) vs. **complement** (one star + shooters) — and
    ask whether complement builds over-perform their *talent*.
    """)
    return


@app.cell
def _(load_mart, load_team_seasons, pd):
    p1c_pl = load_mart("mart_player_league")  # both seasons

    def p1c_agg(g):
        star = g.loc[g["usg"].idxmax()]
        return pd.Series(
            {
                "star_bdn": bool(star["is_ball_dominant_nonshooter"]),
                "n_bdn": int(g["is_ball_dominant_nonshooter"].sum()),
                "n_spacers": int(g["is_shooter"].sum()),
            }
        )

    p1c = (
        p1c_pl.groupby(["season", "team"])
        .apply(p1c_agg, include_groups=False)
        .reset_index()
        .merge(load_team_seasons(), on=["season", "team"])
    )
    p1c = p1c[p1c["star_bdn"]].copy()
    p1c["fit"] = p1c["actual"] - p1c["talent"]
    p1c["build"] = p1c["n_bdn"].apply(
        lambda n: (
            "duplicate (2+ non-shooting stars)"
            if n >= 2
            else "complement (1 star + shooters)"
        )
    )
    p1c_r = p1c["n_bdn"].corr(p1c["fit"])
    p1c_comp = p1c[p1c["n_bdn"] == 1]["fit"].mean()
    p1c_dup = p1c[p1c["n_bdn"] >= 2]["fit"].mean()
    return p1c, p1c_comp, p1c_dup, p1c_r


@app.cell
def _(alt, p1c, pd):
    p1c_z = (
        alt.Chart(pd.DataFrame({"y": [0]}))
        .mark_rule(color="#999", strokeDash=[3, 3])
        .encode(y="y:Q")
    )
    p1c_pts = (
        alt.Chart(p1c)
        .mark_circle(size=130, opacity=0.8)
        .encode(
            x=alt.X("n_spacers:Q", title="shooters on the roster →"),
            y=alt.Y("fit:Q", title="over / under-performance vs. talent (net/100)"),
            color=alt.Color(
                "build:N",
                scale=alt.Scale(
                    domain=[
                        "complement (1 star + shooters)",
                        "duplicate (2+ non-shooting stars)",
                    ],
                    range=["#0A7CD6", "#C0453F"],
                ),
                title="build",
            ),
            tooltip=[
                "team",
                "season",
                "n_bdn",
                "n_spacers",
                alt.Tooltip("fit:Q", format="+.1f"),
            ],
        )
    )
    p1c_lab = (
        alt.Chart(p1c[p1c["team"].isin(["ORL", "NOP"])])
        .mark_text(dx=10, fontSize=11, fontWeight="bold")
        .encode(x="n_spacers:Q", y="fit:Q", text="team:N")
    )
    (p1c_z + p1c_pts + p1c_lab).properties(
        title="Complement builds (blue) over-perform; duplicates (red) under-perform — weak, n=20",
        width=470,
        height=300,
    )
    return


@app.cell
def _(mo, p1c, p1c_comp, p1c_dup, p1c_r):
    mo.md(f"""
    Pooling **both seasons** ({len(p1c)} teams built around a ball-dominant non-shooter):
    teams that **duplicated** the archetype (2+ non-shooting stars) under-performed their talent
    (**{p1c_dup:+.1f}** net/100), while **complement** builds over-performed (**{p1c_comp:+.1f}**)
    — a ~{abs(p1c_comp - p1c_dup):.0f}-point gap in the right direction (correlation of
    duplication with over-performance, r = **{p1c_r:+.2f}**).

    > 🏀 **In plain English:** *duplicating* your non-shooting star tracks under-performing —
    > directionally exactly Orlando's problem. **But it's a weak, small-sample signal** (n = 20,
    > not statistically significant), and **talent dwarfs it.** (The simpler "just count the
    > shooters" version washed out entirely once we added 2024-25 — it was small-sample noise.)
    > This is *consistent with Post 2, not a contradiction:* fit is a small edge, and even this
    > roster-level version is faint. It's why the bet failed both ways — **Orlando duplicated;
    > New Orleans complemented but had bottom-five talent.**

    **The gaps.** n = 20 and underpowered (p ≈ 0.2); net is BBref's, talent is integer-rounded
    DPM. The full Mosley-tenure team pull would firm it up.
    """)
    return


# ============================ POST 2 =========================================
@app.cell
def _(mo):
    mo.md("""
    ---
    # Post 2 · *Fit, quantified*

    **The question.** Once you account for how good the five players are, does "fit"
    (rim protection, size, spacing, ball-movement) actually move the scoreboard — and can
    you just keep stacking talent?

    **The data.** Every team's ~top-20 most-used 5-man lineups, **both** 2024-25 and
    2025-26 (`mart_lineup_features_league` + a held-out rebuild), plus 556 two-man pairs
    (`mart_pair_synergy`). Outcome = lineup **net rating**; talent baseline = **ΣDPM**.

    **The method.** A minutes-weighted regression (team-clustered errors) of net rating
    on talent + fit features; then a *curved* version to test diminishing returns; then a
    held-out replication and a pair-by-pair **WOWY** check.
    """)
    return


@app.cell
def _(fit_std, load_mart, pd, sm):
    p2_league = load_mart("mart_lineup_features_league")
    p2_feats = [
        "talent_sum_dpm",
        "rim_suppress",
        "avg_height_in",
        "spacing_cs_mean",
        "usg_spread",
        "ast_max",
    ]
    p2_nice = {
        "talent_sum_dpm": "talent (ΣDPM)",
        "rim_suppress": "rim protection",
        "avg_height_in": "size",
        "spacing_cs_mean": "spacing (catch & shoot)",
        "usg_spread": "usage balance",
        "ast_max": "playmaking",
    }
    p2_d = p2_league[p2_league["n_covered"] == 5].dropna(subset=p2_feats).copy()
    p2_m = fit_std(p2_d, "net_pts_per100", p2_feats)
    p2_ci = p2_m.conf_int()
    p2_coef = pd.DataFrame(
        {
            "feature": [p2_nice[f] for f in p2_feats],
            "coef": [p2_m.params[f] for f in p2_feats],
            "lo": [p2_ci.loc[f, 0] for f in p2_feats],
            "hi": [p2_ci.loc[f, 1] for f in p2_feats],
            "p": [p2_m.pvalues[f] for f in p2_feats],
        }
    )
    p2_coef["sig"] = p2_coef["p"] < 0.05
    p2_z = (p2_d[p2_feats] - p2_d[p2_feats].mean()) / p2_d[p2_feats].std()
    p2_r2t = (
        sm.WLS(
            p2_d["net_pts_per100"],
            sm.add_constant(p2_z[["talent_sum_dpm"]]),
            weights=p2_d["minutes"],
        )
        .fit()
        .rsquared
    )
    return p2_coef, p2_d, p2_m, p2_r2t


@app.cell
def _(alt, p2_coef, pd):
    p2_zero = (
        alt.Chart(pd.DataFrame({"x": [0]}))
        .mark_rule(color="#999", strokeDash=[3, 3])
        .encode(x="x:Q")
    )
    p2_whisk = (
        alt.Chart(p2_coef)
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
    p2_dots = (
        alt.Chart(p2_coef)
        .mark_point(filled=True, size=90)
        .encode(
            x="coef:Q",
            y=alt.Y("feature:N", sort="-x"),
            color=alt.condition(
                "datum.sig", alt.value("#0A7CD6"), alt.value("#9aa0a6")
            ),
            tooltip=[
                "feature:N",
                alt.Tooltip("coef:Q", format="+.2f"),
                alt.Tooltip("p:Q", format=".3f"),
            ],
        )
    )
    (p2_zero + p2_whisk + p2_dots).properties(
        title="Only rim protection (+) and size (−) move net beyond talent",
        width=460,
        height=200,
    )
    return


@app.cell
def _(mo, p2_m, p2_r2t):
    mo.md(f"""
    Talent alone explains **{p2_r2t:.0%}** of the scoreboard; every fit feature together
    reaches only **{p2_m.rsquared:.0%}**. Of the fit features, **only rim protection (+)
    and size (−) clear zero** — spacing (even measured as catch-and-shoot gravity, the
    real floor-spacing shot) sits flat, as do usage balance and playmaking.
    """)
    return


@app.cell
def _(mo):
    mo.md("""
    **Can you just stack talent?** The regression above is a *straight line*. But there's
    one ball and one rim, so we bend it — let net rating curve as talent piles up (both
    seasons pooled) — and watch it **flatten**.
    """)
    return


@app.cell
def _(alt, load_5man_features_2024, load_mart, np, pd, sm):
    p2_cols = ["team", "net_pts_per100", "talent_sum_dpm", "minutes"]
    p2_25 = load_5man_features_2024()
    p2_25 = p2_25[p2_25["n_covered"] == 5][p2_cols]
    p2_26 = load_mart("mart_lineup_features_league")
    p2_26 = p2_26[p2_26["n_covered"] == 5][p2_cols]
    p2_pool = pd.concat([p2_25, p2_26], ignore_index=True).dropna()
    p2_tc = p2_pool["talent_sum_dpm"] - p2_pool["talent_sum_dpm"].mean()
    p2_q = sm.WLS(
        p2_pool["net_pts_per100"],
        sm.add_constant(pd.DataFrame({"t": p2_tc, "t2": p2_tc**2})),
        weights=p2_pool["minutes"],
    ).fit()
    p2_b1, p2_b2, p2_mean = (
        p2_q.params["t"],
        p2_q.params["t2"],
        p2_pool["talent_sum_dpm"].mean(),
    )
    p2_qt = p2_pool["talent_sum_dpm"].quantile([0.01, 0.5, 0.99])
    p2_marg = pd.DataFrame(
        {
            "lineup talent (ΣDPM)": [
                f"{p2_qt[0.01]:+.0f} (weak)",
                f"{p2_qt[0.5]:+.0f} (middle)",
                f"{p2_qt[0.99]:+.0f} (elite)",
            ],
            "net gained per +1 more DPM": [
                round(p2_b1 + 2 * p2_b2 * (t - p2_mean), 2)
                for t in [p2_qt[0.01], p2_qt[0.5], p2_qt[0.99]]
            ],
        }
    )
    p2_grid = np.linspace(
        p2_pool["talent_sum_dpm"].min(), p2_pool["talent_sum_dpm"].max(), 60
    )
    p2_curve = pd.DataFrame(
        {
            "talent": p2_grid,
            "net": p2_q.params["const"]
            + p2_b1 * (p2_grid - p2_mean)
            + p2_b2 * (p2_grid - p2_mean) ** 2,
        }
    )
    p2_bins = (
        p2_pool.assign(dec=pd.qcut(p2_pool["talent_sum_dpm"], 10, labels=False))
        .groupby("dec")
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
    p2_sat = (
        alt.Chart(p2_curve)
        .mark_line(color="#C0453F", size=2)
        .encode(
            x=alt.X("talent:Q", title="lineup talent — ΣDPM"),
            y=alt.Y("net:Q", title="net rating (points/100)"),
        )
        + alt.Chart(p2_bins)
        .mark_point(filled=True, size=90, color="#0A7CD6")
        .encode(
            x="talent:Q",
            y="net:Q",
            tooltip=[
                alt.Tooltip("talent:Q", format="+.1f"),
                alt.Tooltip("net:Q", format="+.1f"),
            ],
        )
    ).properties(
        title="More talent keeps helping — but less and less (the curve flattens)",
        width=460,
        height=250,
    )
    return p2_b2, p2_marg, p2_sat


@app.cell
def _(p2_sat):
    p2_sat
    return


@app.cell
def _(mo, p2_b2, p2_marg):
    mo.vstack(
        [
            mo.md(
                f"The bend is real (a negative squared term, **{p2_b2:+.3f}**, past the "
                f"noise bar): net rating is **concave** in talent. What each added unit buys:"
            ),
            mo.ui.table(p2_marg, selection=None),
            mo.md("""
        > 🏀 A star added to a **weak** lineup is worth ~2.5 net; added to an **elite**
        > one, almost nothing. Five All-Stars don't give you five All-Stars' worth of
        > scoreboard — there's one ball and one rim, and the sixth good player mostly
        > takes touches from the fifth. **This is the honest "diminishing returns."**
        """),
        ]
    )
    return


@app.cell
def _(fit_std, load_5man_features_2024, load_mart, pd):
    # Held-out replication (2024-25) + pair-WOWY: does the story survive?
    p2_hf = ["talent_sum_dpm", "rim_suppress", "avg_height_in", "spacing_cs_mean"]
    p2_hlab = {
        "talent_sum_dpm": "talent",
        "rim_suppress": "rim protection",
        "avg_height_in": "size",
        "spacing_cs_mean": "spacing",
    }
    p2_24 = load_5man_features_2024()
    p2_24 = p2_24[p2_24["n_covered"] == 5].dropna(subset=p2_hf)
    p2_new = load_mart("mart_lineup_features_league")
    p2_new = p2_new[p2_new["n_covered"] == 5].dropna(subset=p2_hf)

    def p2_verdict(m, col):
        if m.pvalues[col] >= 0.05:
            return "no effect"
        return "helps ✓" if m.params[col] > 0 else "hurts ✓"

    p2_rep = pd.DataFrame(
        [
            {
                "ingredient": p2_hlab[f],
                "2024-25 (held out)": p2_verdict(
                    fit_std(
                        p2_24,
                        "net_pts_per100",
                        ["talent_sum_dpm", f] if f != "talent_sum_dpm" else [f],
                    ),
                    f,
                ),
                "2025-26": p2_verdict(
                    fit_std(
                        p2_new,
                        "net_pts_per100",
                        ["talent_sum_dpm", f] if f != "talent_sum_dpm" else [f],
                    ),
                    f,
                ),
            }
            for f in p2_hf
        ]
    )

    p2_pairs = load_mart("mart_pair_synergy")
    p2_use = fit_std(
        p2_pairs, "complement_centered", ["talent_sum", "usg_min"], weightcol="minutes"
    )
    p2_rim = fit_std(
        p2_pairs, "complement_centered", ["talent_sum", "blk_max"], weightcol="minutes"
    )
    p2_pairtab = pd.DataFrame(
        {
            "pairing": [
                "two ball-dominant players (redundant)",
                "at least one rim protector",
            ],
            "effect on pair performance": [
                round(p2_use.params["usg_min"], 2),
                round(p2_rim.params["blk_max"], 2),
            ],
            "real?": [
                "no" if p2_use.pvalues["usg_min"] >= 0.05 else "yes",
                "yes" if p2_rim.pvalues["blk_max"] < 0.05 else "no",
            ],
        }
    )
    return p2_pairtab, p2_pairs, p2_rep


@app.cell
def _(mo, p2_pairs, p2_pairtab, p2_rep):
    mo.vstack(
        [
            mo.md(
                "**Does it hold up? (a) The story replicates on the held-out 2024-25 season:**"
            ),
            mo.ui.table(p2_rep, selection=None),
            mo.md(
                f"**(b) Pair-by-pair ({len(p2_pairs)} two-man combos) — 'redundant' pairings "
                f"don't drag teams down:**"
            ),
            mo.ui.table(p2_pairtab, selection=None),
        ]
    )
    return


@app.cell
def _(mo):
    mo.md("""
    **The takeaways.**

    > 🏀 Fit is real but small, and it's two things: **talent saturates** (each star adds
    > less), and **rim protection** is the one ingredient that adds beyond talent. Spacing,
    > ball-movement, and "these two clash" stories mostly don't survive — coaches already
    > engineer the bad combos away, and the real limit is how much one lineup can squeeze
    > from one ball. Talent explains ~17%; all fit features add only a few points more.

    **The gaps.** Observational, not causal (fit-built teams also coach/stay-healthy
    better); net rating is opponent-*averaged*, not adjusted; each team's ~top-20 lineups
    only; DPM is integer-rounded; and the rim coefficient is partly **mechanical** (rim
    defense is itself a slice of net rating — deterrence is the cleanest piece).
    """)
    return


@app.cell
def _(load_mart, pd, re, unicodedata):
    # Role coverage: do lineups MISSING a whole role (creator / spacer) even exist? (capstone)
    def p2d_norm(s):
        s = (
            unicodedata.normalize("NFKD", str(s))
            .encode("ascii", "ignore")
            .decode()
            .lower()
        )
        return re.sub(r"\s+(jr\.?|sr\.?|ii|iii|iv)$", "", s.strip())

    def p2d_flast(full):
        p = p2d_norm(full).split()
        return f"{p[0][0]}. {' '.join(p[1:])}" if len(p) > 1 else p2d_norm(full)

    p2d_pl = load_mart("mart_player_league")
    p2d_pl = p2d_pl[p2d_pl["season"] == 2026]
    p2d_flag = {
        (t, p2d_flast(n)): (bool(c), bool(s))
        for t, n, c, s in zip(
            p2d_pl.team, p2d_pl.player_name, p2d_pl.is_creator, p2d_pl.is_shooter
        )
    }
    p2d_lf = load_mart("mart_lineup_features_league")
    p2d_lf = p2d_lf[p2d_lf["n_covered"] == 5].dropna(subset=["talent_sum_dpm"]).copy()

    def p2d_cover(row):
        parts = [p2d_norm(x) for x in row["lineup_key"].split("|")]
        return pd.Series(
            {
                "n_creators": sum(
                    p2d_flag.get((row["team"], p), (False, False))[0] for p in parts
                ),
                "n_spacers": sum(
                    p2d_flag.get((row["team"], p), (False, False))[1] for p in parts
                ),
                "matched": sum((row["team"], p) in p2d_flag for p in parts),
            }
        )

    p2d_lf = pd.concat([p2d_lf, p2d_lf.apply(p2d_cover, axis=1)], axis=1)
    p2d_lf = p2d_lf[p2d_lf["matched"] == 5]
    p2d_n = len(p2d_lf)
    p2d_creator = 1 - (p2d_lf["n_creators"] == 0).mean()
    p2d_spacer = 1 - (p2d_lf["n_spacers"] == 0).mean()
    return p2d_creator, p2d_n, p2d_spacer


@app.cell
def _(mo, p2d_creator, p2d_n, p2d_spacer):
    mo.md(f"""
    **One more nail — why fit stays small even in principle.** The strongest surviving fit
    idea is a *threshold*: a lineup with **no** creator, or **no** spacing at all, should
    crater. We flagged every player's role and checked. Across {p2d_n} leaguewide lineups,
    **{p2d_creator:.0%} have a creator and {p2d_spacer:.0%} have a spacer** — the "no-spacing"
    lineup that should fail *barely exists* (missing a role in ~1–2% of lineups), and where it
    does, net rating doesn't move beyond talent.

    > 🏀 **The capstone:** the fit cliffs are real on paper but not on NBA floors — **coaches
    > engineer them away before they ever play.** That's the deepest reason fit stays small:
    > not that redundancy is harmless, but that the *disasters never get deployed*. Which reframes
    > Orlando's and New Orleans's real problem — not a broken lineup on any given night, but a
    > **ceiling their rosters can't clear.**
    """)
    return


# ============================ POST 3 =========================================
@app.cell
def _(mo):
    mo.md("""
    ---
    # Post 3 · *Know your enemy*

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
        > 🏀 Style is **preparation, not prediction.** The same trait ("they allow threes")
        > raises our 3-point rate but does *nothing* to the final margin. What decides the
        > scoreboard is opponent **quality** and **home court** (~+4 points). "Bad matchup"
        > is mostly a vibe; "better team" is the fact.
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


# ============================ POST 4 =========================================
@app.cell
def _(mo):
    mo.md("""
    ---
    # Post 4 · *The moves that matter*

    **The question.** How many wins does each roster project to — and does a "fit" tweak
    move the needle more than a straight talent upgrade?

    **The data.** Each team's full roster with per-player **DPM** and projected minutes
    (`mart_roster`) — the deep bench included, because that's what drags a bad team.

    **The method.** Team net rating = `5 × minutes-weighted mean DPM`, then **Pythagorean**
    wins (outscore people by more → win more, fit to NBA history). Then a Monte-Carlo
    simulation of the season to turn uncertain minutes/growth into a *range* of wins.
    """)
    return


@app.cell
def _(load_mart, mo, np, pd, q):
    p4_rost = load_mart("mart_roster")

    def p4_pyth(net, exp=13.91, ppg=115.0):
        pf, pa = ppg + net / 2, ppg - net / 2
        return 82 * pf**exp / (pf**exp + pa**exp)

    p4_actual = q("""select regexp_replace(column01,'\\*$','') as team_name, cast(column03 as int) as w
                 from read_csv('s3://nba-fit-lab/raw/bbref/2026-07-08/league_team_advanced.csv',
                 header=false, skip=6, all_varchar=true) where column01 not in ('','League Average')""")

    def p4_sim(tm):
        r = p4_rost[p4_rost["team"] == tm]
        dpm, w = r["dpm"].to_numpy(float), r["mpg"].to_numpy(float)
        base = 5 * (dpm * w).sum() / w.sum()
        rng = np.random.default_rng(0)
        dd = dpm + rng.normal(0, 1.2, (4000, len(dpm)))
        md = w * np.exp(rng.normal(0, 0.15, (4000, len(w))))
        wins = p4_pyth(5 * (dd * md).sum(1) / md.sum(1))
        p5, p50, p95 = np.percentile(wins, [5, 50, 95])
        return base, round(p50), round(p5), round(p95)

    p4_rows = []
    for tm, name in [
        ("ORL", "Orlando Magic"),
        ("NOP", "New Orleans Pelicans"),
        ("OKC", "Oklahoma City Thunder"),
        ("WAS", "Washington Wizards"),
    ]:
        base, p50, p5, p95 = p4_sim(tm)
        aw = int(p4_actual[p4_actual["team_name"] == name]["w"].iloc[0])
        p4_rows.append(
            {
                "team": tm,
                "proj wins (median)": p50,
                "90% range": f"{p5}–{p95}",
                "actual wins": aw,
                "miss": p50 - aw,
            }
        )
    mo.vstack(
        [
            mo.ui.table(pd.DataFrame(p4_rows), selection=None),
            mo.md(
                "Within a couple of wins for good (OKC) and bad (WAS) teams alike — the "
                "**talent + minutes → wins** chain holds, no fit term required. Orlando "
                "projects low-40s, New Orleans high-20s; the **±7-win range** is the honest "
                "part a single number would hide."
            ),
        ]
    )
    return


@app.cell
def _(mo):
    mo.md("""
    **The takeaways.**

    > 🏀 Trust the **range**, not a single projection. And priced through this engine, a
    > genuine **talent** upgrade moves the win range far more than any "fit" tweak — which
    > is Post 2 again: fit is the small correction, talent is the story.

    **The gaps.** These are last season's rosters and minutes; a real forecast needs *next*
    season's (injuries, trades, a young player's leap) — which is exactly why the output is
    a distribution, not a point.
    """)
    return


# ============================ POST 5 =========================================
@app.cell
def _(mo):
    mo.md("""
    ---
    # Post 5 · *Same coach, new roster* — the in-season tracker *(coming)*

    **The question.** Are Posts 1–4's predictions coming true? If fit is mostly *coaching*,
    the new staffs lift New Orleans and Orlando; if it's mostly *roster*, both repeat.

    **The data (coming).** Weekly in-season refreshes of the same sources, as real games
    accumulate.

    **The method.** Track each team's **rim protection** trend first (Post 2 says that's the
    one lever that pays), plus their fit metrics under the new staff, and grade Post 1's bet.

    > 🏀 **Takeaway:** this is the payoff — *"here's what we predicted, and here's whether
    > it's coming true."* Not built yet; it needs a few weeks of new games.

    **The gaps.** No data yet; and with fit this small, expect the signal to be a slow
    aggregate trend, not a dramatic week-to-week swing.
    """)
    return


@app.cell
def _(mo):
    mo.md("""
    ---
    ## The whole series, in one breath

    Talent decides almost everything — and even talent **saturates**, so you can't just
    stack stars. The one "fit" that reliably helps on top is **rim protection**; spacing,
    matchups, and "these two can't play together" are real to *watch* but small on the
    *scoreboard*. Fit is worth pricing — it is not worth mistaking for talent.

    *Reproducible: export the CSVs → `make ingest transform` → open this notebook.
    Sources: Basketball-Reference, PBPStats, DARKO, Cleaning the Glass.*
    """)
    return


@app.cell
def _():
    import re
    import unicodedata

    import altair as alt
    import marimo as mo
    import numpy as np
    import pandas as pd
    import statsmodels.api as sm
    from sklearn.cluster import KMeans
    from sklearn.metrics import adjusted_rand_score, silhouette_score
    from sklearn.preprocessing import StandardScaler

    from _lab import (
        load_5man_features_2024,
        load_games_rim,
        load_mart,
        load_team_seasons,
        q,
    )

    return (
        KMeans,
        StandardScaler,
        adjusted_rand_score,
        alt,
        load_5man_features_2024,
        load_games_rim,
        load_mart,
        load_team_seasons,
        mo,
        np,
        pd,
        q,
        re,
        silhouette_score,
        sm,
        unicodedata,
    )


if __name__ == "__main__":
    app.run()
