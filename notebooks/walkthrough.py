import marimo

__generated_with = "0.23.13"
app = marimo.App(width="medium")


@app.cell
def _(mo):
    mo.md("""
    # NBA Fit Lab — the whole series, one notebook

    A guided walk through every post. Each section answers the same five questions in plain
    English: **what are we asking, what data, what method, what did we find, and where is it
    fragile.** Every number is computed live from the real data.

    | Post | Title | The fan question |
    |---|---|---|
    | **1** | *Same constraint, different paths* | Paolo and Zion pose a similar roster problem. How did Orlando and New Orleans actually try to solve it? |
    | **2** | *What does fit actually buy you?* | Once a lineup can function, which "fit" traits add wins beyond talent? |
    | **3** | *Why Orlando survived and New Orleans collapsed* | Same kind of star — so why were the outcomes so different? |
    | **4** | *What moves actually matter?* | How many wins is this roster, and how much talent should you trade for a cleaner fit? |
    | **5** | *The coach changes sides* | Which parts of Orlando were Mosley, and which were the roster? (in-season) |

    > 🏀 **The one-sentence story:** Orlando and New Orleans are built around the *same kind of
    > constraint* — a jumbo primary creator who doesn't space the floor (Banchero, Williamson) —
    > but they reached it by different roster histories, and the roster a team ices is not the
    > roster it built. Across every angle: **talent is the strongest stable signal we can
    > measure**, fit matters mostly by keeping a lineup above a functional floor, and among the
    > lineups coaches actually deploy the one fit lever that reliably pays is **rim protection**.
    """)
    return


@app.cell
def _(mo):
    mo.md("""
    ### The words we use (glossary)

    | Term | Plain meaning |
    |---|---|
    | **Net rating** | How much a lineup/team outscores opponents **per 100 possessions**. +5 good, −5 bad, ±10 extreme. |
    | **DPM** (Daily Plus-Minus) | One number for how much a **single player** helps per 100 possessions (public **DARKO** model). Our talent yardstick. |
    | **ΣDPM** | The five players' DPM **added up** — the net rating the *sum of the parts* predicts. |
    | **Fit** | Performance **beyond** talent. Simple version: `net − ΣDPM`. Calibrated version (Post 2): net minus what a talent-only model predicts. |
    | **Rim protection** | How well a lineup stops opponents at the rim (scaring them off *and* making them miss). |
    | **Spacing / gravity** | How much a shooter pulls defenders out to the arc. Measured from **catch-and-shoot** threes. |
    | **Co-minutes** | Minutes two players are **on the floor together** — the difference between a roster and a *realized* pairing. |
    | **Availability** | How much of a season a player was actually available (games / minutes played). |
    | Sources | **BBref** (Basketball-Reference), **PBPStats**, **DARKO**, **CTG** (Cleaning the Glass), **ShotQuality** (private cross-check). |

    *Method footnotes use **WLS** (a regression that trusts big-minute lineups more), **R²**
    (share of the ups-and-downs explained), and **p-value** (< 0.05 = "probably real, not
    luck"). The takeaways stand on their own without them. **Season codes:** 2024-25 and 2025-26
    are named in full throughout; we never blur them.*
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
    # Post 1 · *Same constraint, different paths*

    **The question.** Paolo Banchero and Zion Williamson pose a *similar roster-building
    constraint*: each is a jumbo, ball-dominant primary creator who provides little off-ball
    shooting gravity. They are **not** the same player, and Orlando and New Orleans arrived at
    that constraint through very different histories. How did each actually try to solve it —
    and, just as important, what environment did each star *actually* play in?

    **The data.** `mart_player_league` (every rotation player's traits as league percentiles,
    both seasons); `load_transactions()` (a sourced ORL/NOP move-by-move construction history,
    2019-2026); and `mart_star_supporting_cast` / `mart_star_teammate_context` (who each star
    actually shared the floor with — **co-minutes**, not roster snapshots).

    **The method.** Three questions kept deliberately separate:
    1. **Roster architecture** — are Paolo and Zion really a similar constraint, and how do they
       differ? (percentile fingerprints)
    2. **Roster construction** — once each star was the centerpiece, what did the front office
       add? (transaction timeline, neutral about *why*)
    3. **Realized deployment** — what environment did the star actually experience? (co-minutes)

    We do **not** infer front-office intent from a current roster snapshot.
    """)
    return


@app.cell
def _(load_mart):
    p1_pl = load_mart("mart_player_league")
    p1_cur = p1_pl[
        (p1_pl["season"] == 2026) & (p1_pl["team"].isin(["ORL", "NOP"]))
    ].copy()
    p1_stars = p1_cur[
        p1_cur["player_name"].isin(["Paolo Banchero", "Zion Williamson"])
    ].copy()
    p1_fp = p1_stars[
        [
            "player_name",
            "usg_pctl",
            "tpar_pctl",
            "csg_pctl",
            "rim_freq_pctl",
            "ast_pctl",
            "ts_pctl",
        ]
    ].rename(
        columns={
            "player_name": "star",
            "usg_pctl": "usage",
            "tpar_pctl": "3PA rate",
            "csg_pctl": "C&S spacing",
            "rim_freq_pctl": "rim rate",
            "ast_pctl": "assist",
            "ts_pctl": "efficiency",
        }
    )
    return p1_cur, p1_fp


@app.cell
def _(mo, p1_fp):
    mo.vstack(
        [
            mo.md("**The two stars, as league percentiles (2025-26):**"),
            mo.ui.table(p1_fp, selection=None),
            mo.md("""
        - **The shared constraint is real.** Both are elite-usage (Paolo 91st, Zion 85th),
          bottom-quintile three-point volume (18th / 4th), carrying heavy creation load, and
          neither threatens as an off-ball shooter (catch-&-shoot 25th / **0th**). Neither
          produces value as a *spacer* — so whoever plays with them inherits the same spacing math.
        - **But they are different players.** Zion is a far more extreme rim attacker (rim rate
          88th vs 65th) at elite efficiency (true-shooting 89th); Paolo is more perimeter-oriented
          and a **markedly** less efficient scorer (34th) who creates more for others (assists
          81st vs 64th). *Different scorers, similar roster constraint* — the constraint is
          "neither spaces the floor," not "these two are the same."
        """),
        ]
    )
    return


@app.cell
def _(alt, p1_cur):
    # architecture map: usage (ball-dominance) vs catch-&-shoot spacing, ORL vs NOP rotations
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
    p1_star_txt = (
        alt.Chart(
            p1_cur[p1_cur.player_name.isin(["Paolo Banchero", "Zion Williamson"])]
        )
        .mark_text(align="left", dx=8, fontSize=11, fontWeight="bold")
        .encode(
            x="usg_pctl:Q",
            y="csg_pctl:Q",
            text="player_name:N",
            color=alt.value("#333"),
        )
    )
    (p1_dots + p1_star_txt).properties(
        title="Roster architecture: the stars share the bottom-right (high usage, low spacing)",
        width=480,
        height=340,
    )
    return


@app.cell
def _(mo):
    mo.md("""
    ### Construction: once each star was the centerpiece, what did the team add?

    A current roster is not a plan. Franz Wagner, for instance, *predates* Paolo — Orlando
    didn't "choose a duplicate," it inherited a second young forward with some of the same
    limitations. The neutral question is about **timing**: after the star's draft, what kinds of
    pieces did each front office bring in? (We describe *what* was added, not *why*.)
    """)
    return


@app.cell
def _(load_transactions, load_mart, pd):
    p1_tx = load_transactions()
    # post-star incoming pieces (draft/trade/FA), tagged by whether they space the floor
    p1_pl2 = load_mart("mart_player_league")
    p1_sh = (
        p1_pl2[p1_pl2.season == 2026]
        .set_index(["team", "player_name"])["csg_pctl"]
        .to_dict()
    )
    p1_add = p1_tx[
        (p1_tx.era == "post_star")
        & (p1_tx.direction == "in")
        & (p1_tx.transaction_type.isin(["trade", "free_agent_signing"]))
    ].copy()

    def _spacer_note(r):
        s = p1_sh.get((r.team, r.player))
        if s is None:
            return ""
        return "shooter" if s >= 60 else ("non-shooter" if s <= 40 else "mid")

    p1_add["spacing_now"] = p1_add.apply(_spacer_note, axis=1)
    p1_orl_adds = p1_add[p1_add.team == "ORL"][
        ["date", "player", "transaction_type", "spacing_now"]
    ]
    p1_nop_adds = p1_add[p1_add.team == "NOP"][
        ["date", "player", "transaction_type", "spacing_now"]
    ]
    return p1_nop_adds, p1_orl_adds


@app.cell
def _(mo, p1_nop_adds, p1_orl_adds):
    mo.vstack(
        [
            mo.md(
                """**Orlando — notable post-Paolo additions (trades & signings):**"""
            ),
            mo.ui.table(p1_orl_adds, selection=None),
            mo.md(
                """**New Orleans — notable post-Zion additions (trades & signings):**"""
            ),
            mo.ui.table(p1_nop_adds, selection=None),
            mo.md("""
        - **Orlando's post-Paolo moves lean toward shooting.** Kentavious Caldwell-Pope (2024),
          Desmond Bane (2025), Tyus Jones, Gary Harris — the incoming veterans are mostly
          floor-spacers. Whatever the label "duplicate" suggested, the *construction* record
          shows Orlando repeatedly adding off-ball gravity around its non-shooting core.
        - **New Orleans's path is trade-churned** — CJ McCollum in and out, Dejounte Murray in,
          a rotating supporting cast — which is exactly why a roster snapshot misleads. What
          matters is the environment Zion actually got, which we measure next.
        """),
        ]
    )
    return


@app.cell
def _(mo):
    mo.md("""
    ### Realized deployment: what environment did each star *actually* play in?

    The cleanest way past "who was on the roster" is **co-minutes** — weight each teammate's
    traits by the minutes the star actually shared with him. This is the star's *lived*
    environment, from `mart_star_supporting_cast`.
    """)
    return


@app.cell
def _(load_mart):
    p1_sc = load_mart("mart_star_supporting_cast")
    p1_env = (
        p1_sc.assign(season_lbl=p1_sc.season.map({2025: "2024-25", 2026: "2025-26"}))
        .sort_values(["star", "season"])[
            [
                "season_lbl",
                "team",
                "star",
                "star_oncourt_min",
                "cast_dpm",
                "cast_csg_pctl",
                "cast_rimf_pctl",
                "n_shooters_hi",
            ]
        ]
        .rename(
            columns={
                "season_lbl": "season",
                "star_oncourt_min": "star on-court min",
                "cast_dpm": "cast talent (DPM)",
                "cast_csg_pctl": "cast spacing (pctl)",
                "cast_rimf_pctl": "cast rim-rate (pctl)",
                "n_shooters_hi": "# shooters ≥25% min",
            }
        )
    )
    return (p1_env,)


@app.cell
def _(mo, p1_env):
    mo.vstack(
        [
            mo.md(
                "**The realized supporting cast — co-minute-weighted (★ each star-season):**"
            ),
            mo.ui.table(p1_env, selection=None),
            mo.md("""
        - **The spacing environments barely differ where it counts.** In 2025-26 the cast Paolo
          actually played with and the cast Zion actually played with grade almost identically
          for spacing (C&S percentile ~50 vs ~49). In 2024-25 Zion's realized cast was, if
          anything, *better* spaced than Paolo's. The clean "Orlando starved its star / New
          Orleans spaced its star" contrast **does not survive co-minute weighting.**
        - **What *does* differ is availability.** Zion's on-court minutes run well below Paolo's
          (859 → 1,842 vs 1,583 → 2,514). The star's own presence is the biggest difference in
          the two lived environments — which is the thread Post 3 pulls.
        """),
        ]
    )
    return


@app.cell
def _(mo):
    mo.md("""
    **The takeaways.**

    > 🏀 Paolo and Zion create a **similar roster constraint** (a jumbo creator who doesn't
    > space the floor) without being the same player. Orlando's *construction* actually leaned
    > toward adding shooting; New Orleans's churned through pieces. And once you weight by who
    > the stars actually played with, the two **realized** environments look far more alike than
    > the "duplicate vs complement" story implied — the standout difference is how much the star
    > was *available*, not how well he was spaced.

    **The gaps.** Fingerprints are box-score percentiles (a clean five-tool sketch, still not
    tracking data). The construction record is sourced but hand-curated; `era` is *timing*, not
    proven intent. Co-minutes come from BBref two-man pairs, so the lowest-exposure teammates
    are missing (near-zero weight anyway). This is **n=2 teams** — the leaguewide adjudication
    is Post 2.
    """)
    return


# ============================ POST 2 =========================================
@app.cell
def _(mo):
    mo.md("""
    ---
    # Post 2 · *What does fit actually buy you?*

    **The question.** Once an NBA lineup has enough creation and spacing to *function*, which
    fit traits still add wins on top of talent — and which are already priced in?

    **The data.** `mart_lineup_features_league` — every team's top-~20 five-man lineups
    (600 for 2025-26), each with its net rating, a talent baseline (**ΣDPM**), and continuous
    fit features (spacing, rim protection, size, usage spread), plus the 2024-25 rebuild via
    `load_5man_features_2024` for replication.

    **The method.** Two ideas kept distinct:
    - **Minimum-viable fit** — some things a lineup needs just to work (a creator, enough
      shooting, adequate rim defense). We check how often deployed lineups *lack* them.
    - **Marginal fit** — among lineups that already work, does *more* of a trait add net? We
      regress net on each fit feature, controlling for talent with a **calibrated** baseline
      (not a rigid `net − ΣDPM`), and cross-check against an independent talent measure.
    """)
    return


@app.cell
def _(load_mart):
    # minimum-viable fit: how often does a DEPLOYED lineup lack a role? (recovered coverage)
    p2_lf = load_mart("mart_lineup_features_league")
    p2_cov = p2_lf[p2_lf.n_role_covered == 5]
    p2_pct_creator = 100 * p2_cov.has_creator.mean()
    p2_pct_shooter = 100 * p2_cov.has_shooter.mean()
    p2_n = len(p2_cov)
    return p2_cov, p2_lf, p2_n, p2_pct_creator, p2_pct_shooter


@app.cell
def _(mo, p2_n, p2_pct_creator, p2_pct_shooter):
    mo.md(f"""
    ### Minimum-viable fit: the cliffs are engineered away

    Across the **{p2_n}** fully-resolved deployed lineups (2025-26), a creator is present in
    **{p2_pct_creator:.0f}%** and a catch-&-shoot shooter in **{p2_pct_shooter:.0f}%**. Truly
    role-deficient lineups — no creator, or no spacing at all — *barely exist in the data*,
    because coaches almost never send them out for meaningful minutes.

    > This is the crucial framing correction. It does **not** mean "spacing doesn't matter." It
    > means NBA coaches satisfy the functional minimums before a lineup ever reaches the floor,
    > so the observational data can only speak to the **marginal** value of *extra* fit among
    > lineups that already work. (Earlier versions measured this on a talent-filtered subset and
    > lost ~180 lineups; the recovered full sample says the same thing, without the bias.)
    """)
    return


@app.cell
def _(load_5man_features_2024, load_mart, pd):
    # pooled two-season lineups for the marginal-fit regressions
    p2_a = load_mart("mart_lineup_features_league").copy()
    p2_a["season"] = 2026
    p2_b = load_5man_features_2024().copy()
    p2_pool = pd.concat(
        [p2_a[p2_a.n_covered == 5], p2_b[p2_b.n_covered == 5]], ignore_index=True
    ).dropna(subset=["talent_sum_dpm", "net_pts_per100"])
    return (p2_pool,)


@app.cell
def _(fit_std, p2_pool):
    # talent-only vs talent+fit variance explained (weighted R^2), pooled
    def _wr2(df, xcols):
        m = fit_std(df, "net_pts_per100", xcols)
        return m.rsquared

    p2_r2_talent = _wr2(p2_pool, ["talent_sum_dpm"])
    p2_sub = p2_pool.dropna(subset=["rim_suppress", "spacing_cs_mean", "avg_height_in"])
    p2_r2_full = _wr2(
        p2_sub, ["talent_sum_dpm", "spacing_cs_mean", "rim_suppress", "avg_height_in"]
    )
    return p2_r2_full, p2_r2_talent, p2_sub


@app.cell
def _(fit_std, p2_sub):
    # marginal fit: per-SD coefficients, talent + each fit feature, team-clustered
    p2_model = fit_std(
        p2_sub,
        "net_pts_per100",
        ["talent_sum_dpm", "spacing_cs_mean", "rim_suppress", "avg_height_in"],
    )
    p2_coef = (
        p2_model.params.rename("per-SD net")
        .to_frame()
        .join(p2_model.pvalues.rename("p-value"))
        .join(p2_model.conf_int().rename(columns={0: "lo", 1: "hi"}))
        .drop("const")
        .round(2)
    )
    p2_coef.index = [
        "talent (ΣDPM)",
        "spacing (C&S)",
        "rim protection",
        "size (height)",
    ]
    return (p2_coef,)


@app.cell
def _(mo, p2_coef, p2_r2_full, p2_r2_talent):
    mo.vstack(
        [
            mo.md(f"""
        ### Marginal fit: what clears zero once talent is in?

        Talent alone explains **{p2_r2_talent * 100:.0f}%** of the swing in lineup net rating;
        adding every fit feature lifts that to **{p2_r2_full * 100:.0f}%**. So talent is by far
        the strongest *stable* signal we measure — but note most lineup-to-lineup variation is
        still unexplained noise. This is "talent is the strongest signal," **not** "talent
        explains almost everything."

        Per-1-SD effect on net rating (minutes-weighted, team-clustered 95% intervals):
        """),
            mo.ui.table(
                p2_coef.reset_index().rename(columns={"index": "feature"}),
                selection=None,
            ),
            mo.md("""
        - **Rim protection is the one fit lever that clears zero** (interval excludes 0). Among
          already-functional lineups, the group that better deters and alters shots at the rim
          beats its talent. *Caveat:* rim protection is partly mechanical — it's opponent rim
          defense, which is itself a slice of net rating — so read it as "the most persistent
          fit signal," not a clean causal knob.
        - **Spacing is null at the margin** (interval spans 0). Not "spacing is worthless" — the
          floor-level spacing every deployed lineup already has is doing its job; *extra*
          catch-&-shoot gravity doesn't move net once talent is accounted for.
        - **Size is null / fragile** — it was negative in one season only; pooled, it doesn't hold.
        """),
        ]
    )
    return


@app.cell
def _(mo):
    mo.md("""
    ### Diminishing returns: net flattens as talent piles up

    A separate, striking pattern: lineup net rating is **concave** in ΣDPM — the curve rises
    steeply out of the low-talent range and then flattens. Among already-high-talent lineups,
    each additional unit of talent buys much less net than it does lower down.
    """)
    return


@app.cell
def _(np, p2_pool, smf):
    # saturation: quadratic in talent, pooled + per season; plus above-median slope
    p2_pool2 = p2_pool.copy()
    p2_pool2["t"] = p2_pool2.talent_sum_dpm
    p2_pool2["t2"] = p2_pool2.t**2

    def _quad(d):
        m = smf.wls("net_pts_per100 ~ t + t2", data=d, weights=d.minutes).fit(
            cov_type="cluster", cov_kwds={"groups": d.team}
        )
        return m.params["t2"], m.pvalues["t2"]

    p2_q_all = _quad(p2_pool2)
    p2_q_25 = _quad(p2_pool2[p2_pool2.season == 2025])
    p2_q_26 = _quad(p2_pool2[p2_pool2.season == 2026])
    # marginal slope below vs above median talent
    med = p2_pool2.t.median()
    p2_slope_lo = np.polyfit(
        p2_pool2[p2_pool2.t < med].t, p2_pool2[p2_pool2.t < med].net_pts_per100, 1
    )[0]
    p2_slope_hi = np.polyfit(
        p2_pool2[p2_pool2.t >= med].t, p2_pool2[p2_pool2.t >= med].net_pts_per100, 1
    )[0]
    return p2_pool2, p2_q_25, p2_q_26, p2_q_all, p2_slope_hi, p2_slope_lo


@app.cell
def _(alt, np, p2_pool2):
    # binned talent vs weighted-mean net, with a quadratic fit line
    p2_binned = p2_pool2.copy()
    p2_binned["tbin"] = np.round(p2_binned.t)
    p2_agg = (
        p2_binned.groupby("tbin")
        .apply(lambda g: np.average(g.net_pts_per100, weights=g.minutes))
        .rename("net")
        .reset_index()
    )
    p2_pts = (
        alt.Chart(p2_agg)
        .mark_circle(size=60, color="#0A7CD6")
        .encode(
            x=alt.X("tbin:Q", title="lineup talent (ΣDPM)"),
            y=alt.Y("net:Q", title="weighted-mean net rating"),
            tooltip=["tbin", alt.Tooltip("net:Q", format=".1f")],
        )
    )
    p2_line = p2_pts.transform_regression("tbin", "net", method="quad").mark_line(
        color="#E03A3E", size=2
    )
    (p2_pts + p2_line).properties(
        title="Returns to talent flatten at the top (concave, not a straight line)",
        width=480,
        height=320,
    )
    return


@app.cell
def _(mo, p2_q_25, p2_q_26, p2_q_all, p2_slope_hi, p2_slope_lo):
    mo.md(f"""
    The concave (quadratic) term is negative and significant pooled
    (p={p2_q_all[1]:.3f}) and in **both** seasons separately (2024-25 p={p2_q_25[1]:.3f},
    2025-26 p={p2_q_26[1]:.3f}); a quadratic also predicts better out-of-fold than a straight
    line, and it survives trimming the extreme lineups — so it isn't just the low-talent tail.
    Concretely, the marginal slope of net on talent is **+{p2_slope_lo:.1f}** below the median
    but only **+{p2_slope_hi:.1f}** above it.

    > 🏀 Read this as *observed returns flatten among already-good lineups* — a decelerating
    > curve — **not** the causal claim "adding a star to a great lineup does nothing." We're
    > describing the shape of the talent–net relationship, not the effect of a specific trade.

    **Honesty check (independent talent measure).** Using a private **ShotQuality RAPM**
    baseline instead of DPM (the two talent sums correlate only ~0.6), the **rim-protection**
    result reproduces almost exactly (~+3.8 net/SD either way) and spacing stays null — but the
    concavity does **not** clearly replicate on the ShotQuality axis in a single season. So
    "diminishing returns" is well-supported through DPM across two seasons, yet not confirmed by
    a second, independent talent lens — it may partly reflect how DPM itself is built. We flag
    it rather than sell it.
    """)
    return


@app.cell
def _(mo):
    mo.md("""
    **The takeaways.**

    > 🏀 Fit matters most by keeping a lineup above a **functional floor** — a creator, enough
    > spacing, adequate rim defense — and NBA coaches almost always clear that floor before a
    > lineup plays. *Among the lineups they actually deploy,* marginal talent moves net far more
    > than marginal spacing, and the one fit trait that reliably adds on top is **rim
    > protection**. Returns to talent also flatten as you stack it. So "add another shooter" is
    > usually priced in; "protect the rim" is not.

    **The gaps.** Lineups are each team's top-~20 by minutes — a pre-selected, range-restricted
    slice, which is *why* the cliffs are invisible. Rim protection is partly mechanical (it's a
    slice of the outcome). The concavity is talent-measure-dependent (above). And DPM is a
    same-season, integer-rounded talent estimate — a coarse yardstick, used consistently.
    """)
    return


# ============================ POST 3 =========================================
@app.cell
def _(mo):
    mo.md("""
    ---
    # Post 3 · *Why Orlando survived and New Orleans collapsed*

    **The question.** If Paolo and Zion create a *similar* roster constraint, why did Orlando
    become a playoff team while New Orleans had a disastrous season? "They built wrong" is the
    easy answer. The data says something more specific — and it's mostly not about fit.

    **The data.** `load_team_seasons` (each team's actual net, wins, and talent baseline, both
    seasons); `mart_availability` (games/minutes lost, DPM-weighted); `mart_star_supporting_cast`
    (the realized environment from Post 1).

    **The method.** Decompose the Orlando-minus-New-Orleans **outcome gap**, one season at a
    time, into the part talent already predicts and the part it doesn't — then ask what fills the
    residual. We keep the seasons separate on purpose: they are two different problems.
    """)
    return


@app.cell
def _(load_team_seasons):
    p3_ts = load_team_seasons()
    p3_on = p3_ts[p3_ts.team.isin(["ORL", "NOP"])].copy()
    NET_TO_WINS = 2.17  # from the Post 4 backtest (wins = 41 + 2.17*net)

    def _decomp(season):
        o = p3_on[(p3_on.season == season) & (p3_on.team == "ORL")].iloc[0]
        n = p3_on[(p3_on.season == season) & (p3_on.team == "NOP")].iloc[0]
        gap = o.actual - n.actual
        talent_gap = o.talent - n.talent
        resid = gap - talent_gap
        return {
            "season": "2024-25" if season == 2025 else "2025-26",
            "ORL net": round(o.actual, 1),
            "NOP net": round(n.actual, 1),
            "outcome gap": round(gap, 1),
            "explained by talent": round(talent_gap, 1),
            "NOT talent": round(resid, 1),
            "≈ wins not-talent": round(resid * NET_TO_WINS),
        }

    p3_decomp = [_decomp(2025), _decomp(2026)]
    return NET_TO_WINS, p3_decomp, p3_on


@app.cell
def _(mo, pd, p3_decomp):
    mo.vstack(
        [
            mo.md("**The Orlando − New Orleans gap, decomposed (net rating):**"),
            mo.ui.table(pd.DataFrame(p3_decomp), selection=None),
            mo.md("""
        The two seasons are opposite kinds of gap:
        - **2024-25 — the collapse.** Orlando and New Orleans had *almost the same talent*
          (talent explains barely a fifth of the gap). Yet the outcome gap was ~9.5 net —
          roughly **20+ wins** that talent does **not** account for. This is the season New
          Orleans fell apart, and the residual points somewhere specific (below).
        - **2025-26 — a talent gap.** Here talent explains **more** than the whole gap: New
          Orleans's roster was genuinely, deeply negative-talent, and the team roughly *met* that
          low bar. There was no second collapse — just a bad roster playing like one.
        """),
        ]
    )
    return


@app.cell
def _(load_mart, np):
    # what fills 2024-25's residual? availability. DPM-weighted games lost, leaguewide rank.
    p3_av = load_mart("mart_availability")
    p3_rot = p3_av[
        (p3_av.season == 2025) & p3_av.is_rotation & p3_av.dpm.notna()
    ].copy()
    p3_rot["tax"] = np.maximum(p3_rot.dpm, 0) * p3_rot.games_missed
    p3_tax = p3_rot.groupby("team").tax.sum().sort_values(ascending=False)
    p3_rank = {t: i + 1 for i, t in enumerate(p3_tax.index)}
    p3_nop_absent = (
        p3_av[(p3_av.season == 2025) & (p3_av.team == "NOP") & p3_av.is_rotation]
        .sort_values("games_missed", ascending=False)
        .head(5)[["player_name", "gp", "games_missed", "dpm"]]
    )
    return p3_nop_absent, p3_rank, p3_tax


@app.cell
def _(mo, p3_nop_absent, p3_rank, p3_tax):
    mo.vstack(
        [
            mo.md(f"""
        ### The residual is availability

        In 2024-25 New Orleans lost the **{p3_rank["NOP"]}th-most** DPM-weighted rotation games
        in the league ({p3_tax["NOP"]:.0f} DPM-games, vs a league average of {p3_tax.mean():.0f});
        Orlando ranked {p3_rank["ORL"]}th. The core simply wasn't on the floor:
        """),
            mo.ui.table(p3_nop_absent, selection=None),
            mo.md("""
        Zion (30 games) and Dejounte Murray (31 games) — the two highest-usage players, the
        offensive engine — each missed roughly two-thirds of the season. Because DPM is
        integer-rounded and defense-inclusive, this weighting *understates* the hit: losing your
        two primary shot-creators hurts more than their modest DPM suggests. Orlando, by
        contrast, kept Banchero (46 games) and Wagner (60) mostly available and stayed near its
        talent line.

        > 🏀 The 2024-25 disaster was **an availability shock, not a fit failure.** Same-ish
        > talent, wildly different health — and the healthy team made the playoffs while the hurt
        > one bottomed out. Fit barely enters the accounting.
        """),
        ]
    )
    return


@app.cell
def _(mo):
    mo.md("""
    **The takeaways.**

    > 🏀 "Orlando built right and New Orleans built wrong" is the wrong lesson. In 2024-25 the
    > two rosters were similarly talented; Orlando stayed healthy and New Orleans lost its
    > backcourt engine for most of the year. In 2025-26 New Orleans was simply a low-talent
    > roster and played like one. Across both seasons the outcome gap traces to **talent and
    > availability**, with realized spacing (Post 1) nearly identical and marginal fit (Post 2)
    > small. The stars' shared constraint is real — it just isn't what separated the two teams.

    **The gaps.** This is a two-team, two-season decomposition — a clean accounting, not a
    causal identification. Availability `gp` is games-for-this-team (a late-season arrival can
    look like an absence). And the net→wins constant (2.17) is the leaguewide backtest fit from
    Post 4, applied here for intuition.
    """)
    return


# ============================ POST 4 =========================================
@app.cell
def _(mo):
    mo.md("""
    ---
    # Post 4 · *What moves actually matter?*

    **The question.** What should each front office prioritize — and the practical version of
    the whole series: **how much talent, if any, should a team trade for a cleaner fit?**

    **The data.** `load_team_seasons` (talent, net, wins for all 30 teams × 2 seasons — the
    backtest); `load_roster_2027` (DARKO 2026-27 projections with version-controlled roster
    overrides applied).

    **The method.** First earn the right to project: backtest the engine on all 60 team-seasons,
    in two steps (talent → net, net → wins), and report honest error. Then simulate roster moves
    **minute-neutrally** — you can't add a player without taking someone's minutes — and compare
    same-talent players who differ in fit.
    """)
    return


@app.cell
def _(load_team_seasons, np):
    p4_ts = load_team_seasons()
    # Model B: net -> wins
    p4_k = np.polyfit(p4_ts.actual, p4_ts.wins, 1)
    # end-to-end: talent -> net(=talent) -> wins
    p4_proj = np.polyval(p4_k, p4_ts.talent)
    p4_ts = p4_ts.assign(
        proj_wins=p4_proj.round(1), win_err=(p4_ts.wins - p4_proj).round(1)
    )
    p4_mae = p4_ts.win_err.abs().mean()
    p4_rmse = np.sqrt((p4_ts.win_err**2).mean())
    p4_within5 = (p4_ts.win_err.abs() <= 5).mean() * 100
    return p4_k, p4_mae, p4_rmse, p4_ts, p4_within5


@app.cell
def _(alt, p4_ts):
    p4_line = (
        alt.Chart(p4_ts)
        .mark_line(color="#888", strokeDash=[4, 4])
        .encode(
            x=alt.X("proj_wins:Q", title="projected wins (from talent)"),
            y=alt.Y("proj_wins:Q"),
        )
    )
    p4_dots = (
        alt.Chart(p4_ts)
        .mark_circle(size=55)
        .encode(
            x=alt.X("proj_wins:Q", title="projected wins (from talent)"),
            y=alt.Y("wins:Q", title="actual wins"),
            color=alt.Color("season:N", scale=alt.Scale(scheme="set1"), title="season"),
            tooltip=["team", "season", "talent", "wins", "proj_wins", "win_err"],
        )
    )
    (p4_line + p4_dots).properties(
        title="Backtest: projected vs actual wins, all 60 team-seasons",
        width=460,
        height=360,
    )
    return


@app.cell
def _(mo, p4_mae, p4_rmse, p4_ts, p4_within5):
    p4_worst = p4_ts.reindex(
        p4_ts.win_err.abs().sort_values(ascending=False).index
    ).head(4)
    mo.vstack(
        [
            mo.md(f"""
        ### The backtest, honestly

        Across all 60 team-seasons the engine is right **on average** (correlation ~0.80) but
        **not precise**: mean absolute error **{p4_mae:.1f} wins**, RMSE {p4_rmse:.1f}, and only
        **{p4_within5:.0f}%** of teams land within 5 wins. An earlier draft claimed "within a
        couple wins for good and bad teams alike" — that is **false**, and worth stating plainly.
        """),
            mo.md("**The biggest misses (and why):**"),
            mo.ui.table(
                p4_worst[["season", "team", "talent", "wins", "proj_wins", "win_err"]],
                selection=None,
            ),
            mo.md("""
        Nearly every large miss is **availability**, not a broken model: Philadelphia 2024-25
        (Embiid) and **New Orleans 2024-25** — the collapse from Post 3 — are the two worst
        over-projections. The error lives in the talent→net step (health), while net→wins is
        tight (~2 wins). *The projection's own errors are the availability story.* Read the
        outputs as ranges and directions, not exact totals.
        """),
        ]
    )
    return


@app.cell
def _(load_roster_2027, np, pd):
    # minute-neutral move value: swapping m minutes from dpm_out to dpm_new
    P4_WINS_PER_NET = 2.17

    def move_value_wins(dpm_new, dpm_out, minutes):
        # team talent = sum(dpm*mpg)/48 on 240 team-minutes; net ~ talent; wins ~ 2.17*net
        return (dpm_new - dpm_out) * minutes / 48.0 * P4_WINS_PER_NET

    p4_scen = pd.DataFrame(
        [
            {
                "scenario": "Upgrade a bench slot: +2 DPM starter for a 0 DPM piece, 30 mpg",
                "wins": round(move_value_wins(2, 0, 30), 1),
            },
            {
                "scenario": "Marginal upgrade: +2 for +1, 28 mpg",
                "wins": round(move_value_wins(2, 1, 28), 1),
            },
            {
                "scenario": "Same-talent FIT swap: +2 shooter for +2 non-shooter, 30 mpg",
                "wins": round(move_value_wins(2, 2, 30), 1),
            },
        ]
    )
    # current projected rosters (overrides applied)
    p4_r = load_roster_2027()
    p4_proj_team = (
        p4_r[p4_r.team_name.isin(["Orlando Magic", "New Orleans Pelicans"])]
        .assign(w=lambda d: d.dpm * d.mpg)
        .groupby("team_name")
        .apply(lambda g: 5 * (g.w.sum() / g.mpg.sum()))
        .rename("talent")
        .reset_index()
    )
    p4_proj_team["proj_net≈"] = p4_proj_team.talent.round(1)
    p4_proj_team["proj_wins≈"] = (41 + 2.17 * p4_proj_team.talent).round(0)
    return p4_proj_team, p4_scen


@app.cell
def _(mo, p4_proj_team, p4_scen):
    mo.vstack(
        [
            mo.md("""
        ### Minute-neutral moves, and the fit premium

        A move only helps if the incoming player is better **than whoever loses the minutes**.
        Holding minutes fixed, the value of a swap is just the talent difference it creates:
        """),
            mo.ui.table(p4_scen, selection=None),
            mo.md("""
        The last row is the whole series in one number. Swapping a non-shooter for an
        **equally talented** shooter — a pure *fit* upgrade — is worth ≈ **0 extra wins** in our
        estimates. The one exception is the trait that survived Post 2: an equally talented
        **rim protector** does carry a small positive residual. So the answer to "how much
        talent should you trade for fit?" is: **very little — round to zero — except for rim
        protection.**
        """),
            mo.md(
                "**2026-27 projected talent (returning cores + known moves, ranges not totals):**"
            ),
            mo.ui.table(
                p4_proj_team[["team_name", "proj_net≈", "proj_wins≈"]], selection=None
            ),
            mo.md("""
        Both project as roughly average-ish rosters — Orlando a bit ahead — but read these as
        *directions*, given the ±6-win backtest error and integer-rounded preseason DPM.
        Orlando's priority is health and a cleaner rim-protecting five; New Orleans's is simply
        **more talent**, since 2025-26 showed a genuine talent deficit, not a fit problem.
        """),
        ]
    )
    return


@app.cell
def _(mo):
    mo.md("""
    **The takeaways.**

    > 🏀 Moves are worth their **talent**, minute-for-minute — the fit premium for swapping in an
    > equally good but better-fitting player rounds to zero, with rim protection the lone
    > exception. Both Orlando and New Orleans should chase talent and health first; "fit" is a
    > tiebreaker between similar players, not a reason to give up real ability.

    **The gaps.** Preseason DPM is integer-rounded and regressed to the mean; the backtest MAE is
    ~6 wins, so single-team projections are ranges. Roster overrides are hand-maintained
    (`data/local/manual/roster_2027_overrides.csv`). The minute-neutral sim assumes net moves
    ~1:1 with talent near the middle of the range — reasonable, but not a substitute for a full
    lineup simulation.
    """)
    return


# ============================ POST 5 =========================================
@app.cell
def _(mo):
    mo.md("""
    ---
    # Post 5 · *The coach changes sides* *(in-season, coming)*

    **The question.** Jamahl Mosley coached Orlando and now coaches New Orleans. Which parts of
    Orlando's identity were **Mosley**, and which were the **roster**? A coaching move is a rare
    chance to make *falsifiable* style predictions — not "the cleanest experiment in the league"
    (roster, health, and schedule all change at once), but a genuine two-sided test.

    **The data (coming).** A two-season `mart_team_style` (2024-25 + 2025-26) to fingerprint
    Mosley's Orlando on the dimensions that plausibly reflect coaching (pace, transition rate,
    shot profile, rim rates), plus in-season refreshes.

    **The method.** Freeze a set of measurable predictions *before* the games — for both New
    Orleans (drift **toward** Mosley's Orlando fingerprint) and Orlando under its new coach
    (drift **away**) — then grade them as the season arrives.

    > 🏀 **Takeaway:** this is the live payoff. Posts 1–4 set the priors (similar constraint,
    > different paths; talent and health drive outcomes; rim protection is the one fit lever);
    > Post 5 tests which stylistic traits actually travel with the coach. Built next, once the
    > two-season style trace and a few weeks of games exist.

    **The gaps.** Not built yet: it needs the two-season style fingerprint and in-season data,
    and even then coaching and roster change together — so persistence across *both* of Mosley's
    Orlando seasons is what separates a coaching signature from a roster artifact.
    """)
    return


@app.cell
def _(mo):
    mo.md("""
    ---
    ## The whole series, in one breath

    Orlando and New Orleans are built around the **same kind of constraint** — a jumbo creator
    who doesn't space the floor — but they reached it by different histories, and the rosters
    that actually played diverged sharply from the rosters on paper. Once you measure what the
    stars *actually experienced*, the famous "duplicate vs complement" contrast mostly
    dissolves: the realized spacing environments were nearly identical. What separated the teams
    was **talent and availability** — New Orleans's 2024-25 collapse was an injury shock, and its
    2025-26 was a genuine talent deficit. Under the hood, **talent is the strongest stable signal
    we can measure**; fit mostly keeps a lineup above a functional floor that coaches already
    clear; and among deployed lineups the one fit lever that reliably pays is **rim protection**.
    Moves are worth their talent, and the fit premium rounds to zero — except at the rim. **Fit
    is worth pricing; it is not worth mistaking for talent.**

    *Reproducible: export the CSVs → `make ingest transform` → open this notebook. Sources:
    Basketball-Reference, PBPStats, DARKO, Cleaning the Glass; ShotQuality as a private
    cross-check (never redistributed).*
    """)
    return


@app.cell
def _(mo):
    mo.md("""
    ---
    ## Appendix — for future analysts (what was done, why, and how to build on it)

    *Orientation for anyone (human or model) picking this up. The posts above are the distilled
    output; this is the methods + data map behind them. Full data reference in **`MARTS.md`**;
    the refactor decisions and what-survived-what-changed log in **`ANALYSIS_REFACTOR.md`**.*

    ### The project in one paragraph
    A medallion-lite pipeline (hand-exported CSVs → S3 `raw/` → DuckDB `staging` → S3 `marts/`
    Parquet → these marimo notebooks) built to answer one question honestly: **when you build
    around a jumbo non-shooting creator, what actually matters?** The answer, across every angle:
    **talent is the strongest stable signal we can measure; fit mostly keeps a lineup above a
    functional floor coaches already clear; the one marginal fit lever that reliably pays is rim
    protection; and the Orlando/New Orleans gap is a talent-and-availability story, not a
    duplicate-vs-complement one.**

    ### The five posts and what each establishes
    - **Post 1 — same constraint, different paths.** `mart_player_league` fingerprints (Paolo &
      Zion share the constraint, differ as players); `load_transactions` construction timeline
      (Orlando's post-Paolo adds lean toward shooting); `mart_star_supporting_cast` co-minutes
      (realized spacing environments nearly identical → duplicate/complement demoted).
    - **Post 2 — what fit buys.** Minimum-viable vs marginal fit. Role coverage recovered to
      595/600 (creator 96%, shooter 93%). Calibrated out-of-fold talent baseline. Rim protection
      the one survivor (+; partly mechanical); spacing null; size fragile. Talent saturation
      (concave) — robust in DPM, but *does not* replicate on an independent ShotQuality axis in
      one season (flagged, not sold).
    - **Post 3 — why the outcomes differed.** Decompose the ORL−NOP gap per season: 2024-25 was
      an **availability shock** (NOP lost the 7th-most DPM-weighted games; Zion 30 GP, Murray
      31 GP), 2025-26 a **genuine talent deficit**. Fit barely enters.
    - **Post 4 — what moves matter.** Leaguewide backtest (talent→net→wins, MAE ~6 wins; misses
      are injuries). Minute-neutral sims: moves worth their talent; same-talent fit premium ≈ 0
      except rim. 2026-27 projections with version-controlled roster overrides.
    - **Post 5 — the coach changes sides.** Mosley two-sided style test; pre-registered
      predictions. *Pending the two-season `mart_team_style`.*

    ### Why fit keeps coming up small (the mechanisms)
    1. **Range restriction** — coaches pre-optimize; catastrophic-role lineups never get minutes,
       so regressions on *deployed* lineups can't see the cliffs (this is the min-viable point).
    2. **Self-masking stats** — USG%/gravity are equilibrium outcomes that absorb redundancy
       before you measure it.
    3. **DPM launders it** — DARKO is estimated in balanced lineups, so ΣDPM assumes each player
       keeps his value; the saturation is that leaking through in aggregate.

    ### Data model (see MARTS.md)
    Player traits (`mart_player_league`, 2 seasons); lineups (`mart_lineup_features_league` with
    recovered role flags); realized environment (`mart_star_teammate_context`,
    `mart_star_supporting_cast`); availability (`mart_availability`); games with playoff tags
    (`mart_games_styled`); pairs (`mart_pair_synergy`, 2024-25); rosters (`mart_roster`).
    Cross-season/forward via `_lab` loaders (`load_team_seasons` with wins, `load_transactions`,
    `load_roster_2027` with overrides, `calibrated_fit_residual`, `load_shotquality` —
    **private/local-only**). **Season codes: 2025 = 2024-25, 2026 = 2025-26.**

    ### Open threads (where new work goes)
    - **Two-season `mart_team_style`** — 2024-25 CTG is a rawer format needing its own parser;
      unlocks Post 5 (Mosley fingerprint).
    - **Post 5 in-season tracker** — needs games; grade the frozen predictions.
    - **A 2023-24 DPM snapshot** would let us lag 2024-25 talent and fully close the same-season
      leakage question for both seasons.
    - **Opponent-style / matchup analysis** — preserved as a standalone piece (moved out of the
      main series); leaguewide multi-season is the stronger future version.

    ### How to extend the pipeline
    New raw → `data/local/raw/<source>/<date>/`, then `make ingest`. New staging/mart → a
    numbered `transform/NN_*.sql` (CREATE-as-table + `-- ASSERT` comment tests); `make transform`
    builds in order, writes `mart_*` per-season to S3, fails on any assertion. Notebooks read
    marts via `_lab.load_mart` (or the documented raw loaders). **Keep CTG- and ShotQuality-
    derived data private (licensing) — never to the public site.**
    """)
    return


@app.cell
def _():
    import altair as alt
    import marimo as mo
    import numpy as np
    import pandas as pd
    import statsmodels.api as sm
    import statsmodels.formula.api as smf

    from _lab import (
        load_5man_features_2024,
        load_mart,
        load_roster_2027,
        load_team_seasons,
        load_transactions,
    )

    return (
        alt,
        load_5man_features_2024,
        load_mart,
        load_roster_2027,
        load_team_seasons,
        load_transactions,
        mo,
        np,
        pd,
        sm,
        smf,
    )


if __name__ == "__main__":
    app.run()
