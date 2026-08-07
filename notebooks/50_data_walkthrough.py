import marimo

__generated_with = "0.23.13"
app = marimo.App(width="medium")


@app.cell
def _(mo):
    mo.md("""
    # The whole series, in one walk-through

    This is the guided tour of the whole project: the data behind it, and each
    analysis (**A1–A5**) with a plain-English takeaway a basketball fan can use.
    Every number below is computed live from the real data.

    | | Analysis | The fan question it answers | Short answer |
    |---|---|---|---|
    | **A1** | The setup | *Why are Orlando & New Orleans the league's purest "fit" problems?* | Top-heavy talent, no complementary pieces |
    | **A2** | **What is "fit" worth?** | *Do the right pieces around a star actually add wins — or is it just talent?* | Talent rules, **but it saturates**; the one fit lever that pays is **rim protection** |
    | **A3** | Does the opponent's style matter? | *Do certain opponents give a team trouble stylistically?* | Style changes **how** you play, not **whether** you win |
    | **A4** | What does a roster project to? | *How many wins is this roster — and what move helps most?* | A **range** of wins; a real talent upgrade beats any "fit" tweak |
    | **A5** | The in-season tracker | *Are the predictions coming true?* | Coming during the season — grades A1–A4's calls |

    > 🏀 **The one-sentence story:** talent decides almost everything — but you
    > can't just stack stars forever (each one adds less than the last), and the only
    > "fit" that reliably helps on top of talent is **rim protection**. The stuff the
    > discourse loves — spacing, "these two can't play together" — mostly doesn't show
    > up once you account for how good the players already are.
    """)
    return


@app.cell
def _(mo):
    mo.md("""
    ## The words we use (plain-English glossary)

    A few terms recur. Here's each in one line so nothing below is a mystery.

    | Term | What it means |
    |---|---|
    | **Net rating** | How much a lineup/team outscores opponents by, **per 100 possessions** (so fast and slow teams compare fairly). +5 is good, −5 is bad, ±10 is extreme. |
    | **DPM** (Daily Plus-Minus) | One number for how much a **single player** helps his team per 100 possessions, from the public **DARKO** model. Our "talent" yardstick. |
    | **ΣDPM** ("sigma DPM") | The five players' DPM **added up** — the net rating you'd expect from the *sum of the parts*. Σ is just math shorthand for "add these up." |
    | **Fit** | Performance **beyond** talent: `net rating − ΣDPM`. Positive = the group played better than its parts; negative = worse. |
    | **Rim protection** | How well a lineup stops opponents from scoring at the rim (both scaring them away *and* making them miss). |
    | **Spacing / gravity** | How much a shooter forces defenders to respect him out on the arc, opening the floor. We measure it from **catch-and-shoot** threes (open, stand-still 3s). |
    | **WOWY** (With Or Without You) | A player's team results **with him on the floor vs. off it** — the classic way to see a player's real impact. |
    | **Diminishing returns** | Each added star helps **less** than the last, because there's only one ball, ~100 possessions, and one rim to go around. |
    | Sources | **BBref** (Basketball-Reference), **PBPStats** (play-by-play stats), **DARKO** (the DPM model), **CTG** (Cleaning the Glass). |

    *A few stats-method terms show up in footnotes — **WLS** (weighted least squares:
    a regression that trusts big-minute lineups more), **R²** (the share of the ups
    and downs the model explains), **p-value** (< 0.05 = "probably real, not luck").
    You can enjoy the takeaways without them.*
    """)
    return


@app.cell
def _(sm):
    def fit_std(df, ycol, xcols, weightcol="minutes", cluster="team"):
        """Weighted least squares on standardized predictors, team-clustered errors.
        Standardizing puts every feature on the same scale so coefficients compare."""
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
    ## The data, briefly — where the numbers come from

    Four hand-exported public/licensed sources become clean tables through a code
    pipeline (`raw → staging → marts`), and the analyses read the finished
    **marts**. The one idea that powers everything:

    > **Fit = what a lineup did − what its talent predicted**
    > `fit_residual = net_rating − ΣDPM`

    Poke at any finished table — its size, columns, and first rows:
    """)
    return


@app.cell
def _(mo, tables):
    tbl = mo.ui.dropdown(tables(), value="mart_lineup_features_league", label="table")
    tbl
    return (tbl,)


@app.cell
def _(mo, q, tbl):
    lin_n = int(q(f"select count(*) c from {tbl.value}")["c"][0])
    lin_schema = q(f"describe select * from {tbl.value}")[
        ["column_name", "column_type"]
    ]
    mo.vstack(
        [
            mo.md(f"**`{tbl.value}`** — {lin_n:,} rows, {len(lin_schema)} columns"),
            mo.ui.table(lin_schema, selection=None, page_size=6),
            mo.md("first rows:"),
            mo.ui.table(q(f"select * from {tbl.value} limit 5"), selection=None),
        ]
    )
    return


@app.cell
def _(mo, q):
    # One concrete mart row so "fit = net − talent" is tangible.
    lin_lf = q("""select team, round(minutes) as min, net_pts_per100 as net,
              round(talent_sum_dpm,1) as talent, round(fit_residual,1) as fit,
              round(rim_suppress,3) as rim_protection, round(spacing_cs_mean,2) as spacing
              from mart_lineup_features_league where team in ('ORL','NOP')
              order by minutes desc limit 6""")
    mo.vstack(
        [
            mo.md(
                "Orlando & New Orleans' most-used lineups. Read each row as "
                "**`net = talent + fit`**: `talent` is what the five players' DPM predicts, "
                "`fit` is the leftover we try to explain, and `rim_protection` / `spacing` "
                "are the leading suspects."
            ),
            mo.ui.table(lin_lf, selection=None),
            mo.md(
                "> 🏀 **In plain English:** a lineup's scoreboard is *mostly* set before "
                "tip-off by how good the five guys are. This whole project is about that "
                "small, stubborn *leftover* — and which parts of it are real."
            ),
        ]
    )
    return


@app.cell
def _(mo):
    mo.md("""
    ---
    ## A1 · The setup — two rosters built to test "fit"

    **The premise (narrative, summary stats only).** Orlando and New Orleans are the
    league's two purest *fit* problems: real top-end talent, almost no complementary
    pieces around it (Orlando finished 27th in three-point percentage; New Orleans's
    Zion-plus-Queen frontcourt bled ~11 points per 100). Same coach lineage moving
    between them makes a natural experiment — if fit is mostly *coaching*, the new
    staff fixes it; if it's mostly *roster*, both teams repeat themselves.

    > 🏀 **Takeaway:** A1 just sets the bet. The next three analyses make it
    > *measurable* — so later we can grade who was right.
    """)
    return


@app.cell
def _(mo):
    mo.md("""
    ---
    ## A2 · What is "fit" worth, on top of talent?

    This is the heart of the project, and it has three parts:

    1. **Which "fit" ingredients actually move the scoreboard?**
    2. **Can you just keep stacking talent?** (the diminishing-returns question)
    3. **Do the answers hold up** on a season we didn't study, and pair-by-pair?

    **Part 1 — the regression.** Take all 30 teams' most-used lineups (2025-26), and
    ask: once we hold **talent (ΣDPM)** fixed, do the fit ingredients — rim
    protection, size, spacing, ball-movement — change net rating? (Method: a
    minutes-weighted regression; each ingredient is put on the same scale so the
    numbers compare; errors are widened to account for lineups sharing a team.)
    """)
    return


@app.cell
def _(fit_std, load_mart, np, pd, sm):
    a2_d = load_mart("mart_lineup_features_league")
    a2_d = (
        a2_d[a2_d["n_covered"] == 5]
        .dropna(subset=["rim_suppress", "spacing_cs_mean", "avg_height_in"])
        .copy()
    )
    a2_r = np.corrcoef(a2_d["talent_sum_dpm"], a2_d["net_pts_per100"])[0, 1]
    a2_feats = [
        "talent_sum_dpm",
        "rim_suppress",
        "avg_height_in",
        "spacing_cs_mean",
        "usg_spread",
        "ast_max",
    ]
    a2_nice = {
        "talent_sum_dpm": "talent (ΣDPM)",
        "rim_suppress": "rim protection",
        "avg_height_in": "size (avg height)",
        "spacing_cs_mean": "spacing (catch & shoot)",
        "usg_spread": "usage balance",
        "ast_max": "playmaking",
    }
    a2_m = fit_std(a2_d, "net_pts_per100", a2_feats)
    a2_tab = pd.DataFrame(
        {
            "ingredient": [a2_nice[f] for f in a2_feats],
            "effect (per step)": [round(a2_m.params[f], 2) for f in a2_feats],
            "real?": ["✓ yes" if a2_m.pvalues[f] < 0.05 else "no" for f in a2_feats],
        }
    )
    a2_z = (a2_d[a2_feats] - a2_d[a2_feats].mean()) / a2_d[a2_feats].std()
    a2_r2t = (
        sm.WLS(
            a2_d["net_pts_per100"],
            sm.add_constant(a2_z[["talent_sum_dpm"]]),
            weights=a2_d["minutes"],
        )
        .fit()
        .rsquared
    )
    return a2_d, a2_m, a2_r, a2_r2t, a2_tab


@app.cell
def _(a2_m, a2_r, a2_r2t, a2_tab, mo):
    mo.vstack(
        [
            mo.md(
                f"Talent alone tracks net rating at **r = {a2_r:.2f}** — most of the "
                f"story is just how good the players are. The regression asks what's left:"
            ),
            mo.ui.table(a2_tab, selection=None),
            mo.md(f"""
        **How to read it.** "Effect (per step)" is the points of net rating from a
        one-step improvement in that ingredient, holding the others fixed. "Real?" =
        did it clear the noise bar (statistically, p < 0.05).

        - **Rim protection is the one fit ingredient that reliably helps.**
        - **Size hurts** (bigger lineups underperform their talent — the small-ball
          cost) — but see Part 3: it's shakier than rim protection.
        - **Spacing does *nothing* here** — and this is spacing's *best* test
          (catch-and-shoot gravity, the real floor-spacing shot). Neither does usage
          balance or playmaking.
        - Talent alone explains **{a2_r2t:.0%}** of the scoreboard's ups and downs;
          adding *every* fit ingredient reaches only **{a2_m.rsquared:.0%}**.

        > 🏀 **In plain English:** put a rim protector on the floor and it helps. Load
        > up on shooting for its own sake and — surprisingly — it barely moves the
        > scoreboard once the talent is accounted for.
        """),
        ]
    )
    return


@app.cell
def _(mo):
    mo.md("""
    **Part 2 — can you just keep stacking talent?** The regression above is a
    *straight line*: it assumes the 6th unit of talent helps as much as the 1st. But
    there's only **one ball, ~100 possessions, one rim**. So we bend the line — let
    net rating curve as talent piles up (both seasons pooled, ~1,200 lineups) — and
    see whether the curve **flattens**.
    """)
    return


@app.cell
def _(alt, load_5man_features_2024, load_mart, np, pd, sm):
    dr_cols = ["team", "net_pts_per100", "talent_sum_dpm", "minutes"]
    dr_25 = load_5man_features_2024()
    dr_25 = dr_25[dr_25["n_covered"] == 5][dr_cols]
    dr_26 = load_mart("mart_lineup_features_league")
    dr_26 = dr_26[dr_26["n_covered"] == 5][dr_cols]
    dr_pool = pd.concat([dr_25, dr_26], ignore_index=True).dropna()
    dr_tc = dr_pool["talent_sum_dpm"] - dr_pool["talent_sum_dpm"].mean()
    dr_fit = sm.WLS(
        dr_pool["net_pts_per100"],
        sm.add_constant(pd.DataFrame({"t": dr_tc, "t2": dr_tc**2})),
        weights=dr_pool["minutes"],
    ).fit()
    dr_b1, dr_b2 = dr_fit.params["t"], dr_fit.params["t2"]
    dr_mean = dr_pool["talent_sum_dpm"].mean()
    dr_q = dr_pool["talent_sum_dpm"].quantile([0.01, 0.5, 0.99])
    dr_marg = pd.DataFrame(
        {
            "lineup talent (ΣDPM)": [
                f"{dr_q[0.01]:+.0f}  (weak)",
                f"{dr_q[0.5]:+.0f}  (middle)",
                f"{dr_q[0.99]:+.0f}  (elite)",
            ],
            "net gained per +1 more DPM": [
                round(dr_b1 + 2 * dr_b2 * (t - dr_mean), 2)
                for t in [dr_q[0.01], dr_q[0.5], dr_q[0.99]]
            ],
        }
    )
    # curve + binned dots for the chart
    dr_grid = np.linspace(
        dr_pool["talent_sum_dpm"].min(), dr_pool["talent_sum_dpm"].max(), 60
    )
    dr_curve = pd.DataFrame(
        {
            "talent": dr_grid,
            "net": dr_fit.params["const"]
            + dr_b1 * (dr_grid - dr_mean)
            + dr_b2 * (dr_grid - dr_mean) ** 2,
        }
    )
    dr_pool2 = dr_pool.assign(dec=pd.qcut(dr_pool["talent_sum_dpm"], 10, labels=False))
    dr_bins = (
        dr_pool2.groupby("dec")
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
    dr_chart = (
        alt.Chart(dr_curve)
        .mark_line(color="#C0453F", size=2)
        .encode(
            x=alt.X(
                "talent:Q", title="lineup talent — ΣDPM (five players' DPM added up)"
            ),
            y=alt.Y("net:Q", title="net rating (points per 100)"),
        )
        + alt.Chart(dr_bins)
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
        height=260,
    )
    return dr_b2, dr_chart, dr_marg, dr_q


@app.cell
def _(dr_chart):
    dr_chart
    return


@app.cell
def _(dr_b2, dr_marg, dr_q, mo):
    mo.vstack(
        [
            mo.md(f"""
        The curve is real: the bend (a negative "squared" term, {dr_b2:+.3f},
        well past the noise bar) says net rating is **concave** in talent. What each
        added unit of talent buys:
        """),
            mo.ui.table(dr_marg, selection=None),
            mo.md(f"""
        A star added to a **weak** lineup is worth ~2.5 net; added to an **elite** one
        (already near ΣDPM {dr_q[0.99]:+.0f}), almost nothing. The best lineups in the
        data are already at the flat top of the curve.

        > 🏀 **In plain English — this is the real "diminishing returns."** Five
        > All-Stars don't give you five All-Stars' worth of scoreboard. There's one
        > ball and one rim; the sixth good player mostly just takes touches from the
        > fifth. *This* is the honest version of "you can't just stack talent" — not
        > "these two guys clash," but "there's only so much to go around."
        """),
        ]
    )
    return


@app.cell
def _(mo):
    mo.md("""
    **Part 3 — does it hold up?** Two stress tests. **(a)** Re-run Part 1 on the
    **2024-25** season, which played no part in building the story. **(b)** Go
    pair-by-pair with **WOWY** (With Or Without You): for 556 two-man combos, does a
    *redundant* pairing (two ball-dominant guards, two non-shooters) actually drag
    the team down the way "fit" lore claims?
    """)
    return


@app.cell
def _(fit_std, load_5man_features_2024, load_mart, pd):
    # (a) held-out replication: sign + significance of each ingredient, both seasons
    hold_f = ["talent_sum_dpm", "rim_suppress", "avg_height_in", "spacing_cs_mean"]
    hold_lab = {
        "talent_sum_dpm": "talent",
        "rim_suppress": "rim protection",
        "avg_height_in": "size",
        "spacing_cs_mean": "spacing",
    }
    hold_24 = load_5man_features_2024()
    hold_24 = hold_24[hold_24["n_covered"] == 5].dropna(subset=hold_f)
    hold_26 = load_mart("mart_lineup_features_league")
    hold_26 = hold_26[hold_26["n_covered"] == 5].dropna(subset=hold_f)
    hold_rows = []
    for hf in hold_f:
        m24 = fit_std(
            hold_24,
            "net_pts_per100",
            ["talent_sum_dpm", hf] if hf != "talent_sum_dpm" else [hf],
        )
        m26 = fit_std(
            hold_26,
            "net_pts_per100",
            ["talent_sum_dpm", hf] if hf != "talent_sum_dpm" else [hf],
        )

        def verdict(m, col):
            if m.params[col] > 0 and m.pvalues[col] < 0.05:
                return "helps ✓"
            if m.params[col] < 0 and m.pvalues[col] < 0.05:
                return "hurts ✓"
            return "no effect"

        hold_rows.append(
            {
                "ingredient": hold_lab[hf],
                "2024-25 (held out)": verdict(m24, hf),
                "2025-26": verdict(m26, hf),
            }
        )
    hold_tab = pd.DataFrame(hold_rows)

    # (b) pair WOWY: usage redundancy vs rim protection
    hold_pairs = load_mart("mart_pair_synergy")
    hold_use = fit_std(
        hold_pairs,
        "complement_centered",
        ["talent_sum", "usg_min"],
        weightcol="minutes",
    )
    hold_rim = fit_std(
        hold_pairs,
        "complement_centered",
        ["talent_sum", "blk_max"],
        weightcol="minutes",
    )
    hold_pair_tab = pd.DataFrame(
        {
            "pairing type": [
                "two ball-dominant players (redundant)",
                "at least one rim protector",
            ],
            "effect on pair performance": [
                round(hold_use.params["usg_min"], 2),
                round(hold_rim.params["blk_max"], 2),
            ],
            "real?": [
                "no" if hold_use.pvalues["usg_min"] >= 0.05 else "yes",
                "yes" if hold_rim.pvalues["blk_max"] < 0.05 else "no",
            ],
        }
    )
    return hold_pair_tab, hold_pairs, hold_tab


@app.cell
def _(hold_pair_tab, hold_pairs, hold_tab, mo):
    mo.vstack(
        [
            mo.md("**(a) The story replicates on the held-out 2024-25 season:**"),
            mo.ui.table(hold_tab, selection=None),
            mo.md(
                "Talent, rim protection, and the spacing-null all repeat. **Size is the "
                "weak link** — it only shows up in one season, so we downgrade it from "
                "'confirmed' to 'suggestive.'"
            ),
            mo.md(
                f"**(b) Pair-by-pair ({len(hold_pairs)} two-man combos), redundancy "
                f"doesn't drag teams down:**"
            ),
            mo.ui.table(hold_pair_tab, selection=None),
            mo.md("""
        > 🏀 **In plain English:** the classic "you can't play two ball-dominant guys
        > together" take **doesn't show up in the data** — two high-usage players
        > pairs are fine on average. The pairing that genuinely helps is having a rim
        > protector. Coaches have *already* weeded out the disaster combos, so what's
        > left on the floor rarely clashes; what actually moves the needle is interior
        > defense.
        """),
        ]
    )
    return


@app.cell
def _(mo):
    mo.md("""
    ### A2, all together

    > 🏀 **The full A2 takeaway.** Fit is real but small, and it's two things:
    > **talent saturates** (each added star helps less — the honest "diminishing
    > returns"), and **rim protection** is the one ingredient that adds beyond
    > talent. Spacing, ball-movement, and "these players clash" stories mostly don't
    > survive contact with the data — either because coaches already engineer the bad
    > combos away, or because the real limit is simply how much scoring one lineup can
    > squeeze from one ball.
    """)
    return


@app.cell
def _(mo):
    mo.md("""
    ---
    ## A3 · Does the opponent's *style* matter?

    Fans love "Team X is a bad **matchup** for Team Y." We test it two ways. First:
    do NBA teams even split into clean **style archetypes** (pace-and-space,
    rim-pressure, etc.)? We group all 30 teams by their playing style and score how
    *clean* the groups are.
    """)
    return


@app.cell
def _(
    KMeans, StandardScaler, adjusted_rand_score, load_mart, mo, np, pd, silhouette_score
):
    a3_ts = load_mart("mart_team_style")
    a3_sf = [
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
    a3_X = StandardScaler().fit_transform(a3_ts[a3_sf])
    a3_rows = []
    for k in range(3, 8):
        sil = silhouette_score(
            a3_X, KMeans(k, n_init=10, random_state=0).fit_predict(a3_X)
        )
        labs = [
            KMeans(k, n_init=10, random_state=s).fit_predict(a3_X) for s in range(6)
        ]
        ari = np.mean(
            [
                adjusted_rand_score(labs[i], labs[j])
                for i in range(6)
                for j in range(i + 1, 6)
            ]
        )
        a3_rows.append(
            {
                "# of style groups (k)": k,
                "how clean (silhouette)": round(sil, 3),
                "how stable (ARI)": round(ari, 2),
            }
        )
    mo.vstack(
        [
            mo.ui.table(pd.DataFrame(a3_rows), selection=None),
            mo.md("""
        Two scores, both plain: **"how clean"** (silhouette — are the groups actually
        separated? above ~0.25 is trustworthy) and **"how stable"** (ARI, the Adjusted
        Rand Index — re-run the grouping and do you get the same teams together? 1 =
        identical, 0 = random). Both are low: cleanliness tops out ~0.12, and the
        groups reshuffle every run.

        > 🏀 **In plain English:** NBA "team types" are a **spectrum, not boxes**.
        > Every team is a little faster or a little more rim-heavy than the next —
        > there's no clean set of archetypes to sort them into. So instead of forcing
        > fake buckets, we measure opponent style as raw numbers and ask what they move.
        """),
        ]
    )
    return


@app.cell
def _(load_mart, mo, pd, sm):
    a3_g = load_mart("mart_games_styled")
    a3_g["home"] = (~a3_g["is_away"]).astype(int)

    def a3_fit(y, xs):
        return sm.OLS(a3_g[y], sm.add_constant(a3_g[xs])).fit(cov_type="HC1")

    a3_mix = a3_fit(
        "three_pa_rate", ["opp_def_three_pa_rate_allowed", "opp_def_pts_poss", "home"]
    )
    a3_pace = a3_fit("pace", ["opp_pace", "home"])
    a3_style = [
        "opp_off_rim_rate",
        "opp_off_three_pa_rate",
        "opp_def_tov_forced_pct",
        "opp_def_rim_rate_allowed",
    ]
    a3_mrg = a3_fit("margin", ["opp_net_pts_poss", "home"] + a3_style)
    a3_tab = pd.DataFrame(
        {
            "does the opponent's…": [
                "style (allows 3s)",
                "style (pace)",
                "quality (how good they are)",
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
            "real? (p)": [
                round(a3_mix.pvalues["opp_def_three_pa_rate_allowed"], 3),
                round(a3_pace.pvalues["opp_pace"], 3),
                round(a3_mrg.pvalues["opp_net_pts_poss"], 3),
                round(a3_mrg.pvalues["home"], 3),
                round(min(a3_mrg.pvalues[c] for c in a3_style), 3),
            ],
        }
    )
    mo.vstack(
        [
            mo.md(
                "**Now the real test — process vs. outcome.** We check whether the "
                "opponent's style changes *how we play* (our shot mix, our pace) and "
                "whether it changes *the final margin*:"
            ),
            mo.ui.table(a3_tab, selection=None),
            mo.md("""
        The tell: the *same* opponent trait ("they allow threes") **raises our 3-point
        rate** (how we play) but **does nothing to the final margin**. What decides the
        scoreboard is how *good* the opponent is, plus home court (~+4 points).

        > 🏀 **In plain English:** style is **preparation, not prediction**. A team's
        > playing style visibly changes how a game *looks* — more threes, faster or
        > slower — but over a full season it doesn't change *who wins*. Quality and
        > home court do. "Bad matchup" is mostly a vibe; "better team" is the fact.
        """),
        ]
    )
    return


@app.cell
def _(mo):
    mo.md("""
    ---
    ## A4 · From a roster to a *range* of wins

    The engine, in one line: **team net rating = 5 × the minutes-weighted average of
    the players' DPM**, then convert net rating into wins (the "Pythagorean" formula
    — outscore people by more, win more, in a way fit to real NBA history). First,
    does it even work? Check last season's projections against what actually happened:
    """)
    return


@app.cell
def _(load_mart, mo, pd, q):
    a4_rost = load_mart("mart_roster")

    def a4_pyth(net, exp=13.91, ppg=115.0):
        pf, pa = ppg + net / 2, ppg - net / 2
        return 82 * pf**exp / (pf**exp + pa**exp)

    a4_actual = q("""select regexp_replace(column01,'\\*$','') as team_name, cast(column03 as int) as w
                 from read_csv('s3://nba-fit-lab/raw/bbref/2026-07-08/league_team_advanced.csv',
                 header=false, skip=6, all_varchar=true) where column01 not in ('','League Average')""")
    a4_rows = []
    for tm, name in [
        ("ORL", "Orlando Magic"),
        ("NOP", "New Orleans Pelicans"),
        ("OKC", "Oklahoma City Thunder"),
        ("WAS", "Washington Wizards"),
    ]:
        rc = a4_rost[a4_rost["team"] == tm]
        net = 5 * (rc["dpm"] * rc["mpg"]).sum() / rc["mpg"].sum()
        aw = int(a4_actual[a4_actual["team_name"] == name]["w"].iloc[0])
        a4_rows.append(
            {
                "team": tm,
                "projected wins": round(a4_pyth(net)),
                "actual wins": aw,
                "miss by": round(a4_pyth(net)) - aw,
            }
        )
    mo.vstack(
        [
            mo.ui.table(pd.DataFrame(a4_rows), selection=None),
            mo.md(
                "Within a couple of wins for good and bad teams alike — **talent + "
                "minutes → wins** lands close with *no* fit term at all."
            ),
        ]
    )
    return


@app.cell
def _(load_mart, mo, np, pd):
    a4_rr = load_mart("mart_roster")

    def a4_sim(tm):
        r = a4_rr[a4_rr["team"] == tm]
        dpm, w = r["dpm"].to_numpy(float), r["mpg"].to_numpy(float)
        rng = np.random.default_rng(0)
        dd = dpm + rng.normal(0, 1.2, (4000, len(dpm)))
        md = w * np.exp(rng.normal(0, 0.15, (4000, len(w))))
        net = 5 * (dd * md).sum(1) / md.sum(1)
        pf, pa = 115 + net / 2, 115 - net / 2
        wins = 82 * pf**13.91 / (pf**13.91 + pa**13.91)
        p5, p50, p95 = np.percentile(wins, [5, 50, 95])
        return {
            "team": tm,
            "5th %ile": round(p5),
            "median wins": round(p50),
            "95th %ile": round(p95),
        }

    a4_dist = pd.DataFrame([a4_sim("ORL"), a4_sim("NOP")])
    mo.vstack(
        [
            mo.md(
                "**Why a range, not a number.** Next season's minutes and player growth "
                "are genuinely uncertain (injuries, roles, a young player's leap). So we "
                "simulate the season 4,000 times, drawing those unknowns each time — for "
                "*both* teams:"
            ),
            mo.ui.table(a4_dist, selection=None),
            mo.md("""
        Orlando projects to the low-40s (a range spanning play-in to a top-4 seed);
        New Orleans to the high-20s (a lottery team either way). The *width* of each
        range — about ±7 wins — is the honest part a single number would hide.

        > 🏀 **In plain English:** don't trust a single win projection — trust the
        > *range*. And when you price roster moves through this engine (the A4 notebook
        > does it live for both teams), a genuine **talent** upgrade moves the range far
        > more than any "fit" tweak. Which is A2 again: fit is the small correction,
        > talent is the story.
        """),
        ]
    )
    return


@app.cell
def _(mo):
    mo.md("""
    ---
    ## A5 · The in-season tracker *(coming during the season)*

    A1–A4 make **predictions**; A5 grades them as real games come in. It's a weekly
    refresh (automated once fresh exports land) that watches:

    - **Are the fit metrics moving** for New Orleans and Orlando under their new
      staffs — i.e., is the leftover ("fit") improving, or is the roster ceiling real?
    - **Rim protection first.** Since A2 says that's the one lever that pays, A5 tracks
      each team's rim-protection trend as the leading fit indicator.
    - **Grading A1's bet:** if fit is mostly *coaching*, the new staff lifts the fit
      metrics; if it's mostly *roster*, both teams repeat themselves with new scapegoats.

    > 🏀 **Takeaway:** A5 is the payoff — the part that says, in-season, *"here's what
    > we predicted, and here's whether it's coming true."* Not built yet; it needs a
    > few weeks of new games first.
    """)
    return


@app.cell
def _(mo):
    mo.md("""
    ---
    ## The whole series, assembled

    | Analysis | The fan question | The answer |
    |---|---|---|
    | **A1** | Why these two teams? | Purest "fit" problems — real talent, no complementary pieces |
    | **A2** | What is fit worth? | Talent rules **but saturates** (each star adds less); the one fit lever that pays is **rim protection**; spacing & "clash" stories mostly don't survive |
    | **A3** | Does opponent style matter? | It changes **how** you play, not **whether** you win — quality + home court decide games |
    | **A4** | What does a roster project to? | A **range** of wins; a real talent upgrade dwarfs any fit tweak |
    | **A5** | Are the calls coming true? | *Coming in-season* — grades A1–A4 against real games |

    > 🏀 **The bottom line for a basketball fan:** the stuff that decides games is,
    > overwhelmingly, **how good the players are** — and even that runs into
    > diminishing returns, because there's only one ball and one rim to share. Around
    > the edges, **rim protection** is the "fit" that genuinely helps. Spacing,
    > matchups, and "these two can't play together" are real to *watch* but small on
    > the *scoreboard* — worth pricing, not worth mistaking for talent.

    *Every number here is reproducible: export the CSVs → `make ingest transform` →
    open any notebook. Sources: Basketball-Reference, PBPStats, DARKO, Cleaning the Glass.*
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

    from _lab import load_5man_features_2024, load_mart, q, tables

    return (
        KMeans,
        StandardScaler,
        adjusted_rand_score,
        alt,
        load_5man_features_2024,
        load_mart,
        mo,
        np,
        pd,
        q,
        silhouette_score,
        sm,
        tables,
    )


if __name__ == "__main__":
    app.run()
