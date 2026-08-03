import marimo

__generated_with = "0.23.13"
app = marimo.App(width="medium")


@app.cell
def _(mo):
    mo.md("""
    # From raw exports to conclusions — a data walkthrough

    This notebook traces the whole pipeline behind A2–A4: the four raw data
    sources, how they're cleaned into **staging** views, how those become the
    **marts** the analyses read, and exactly how each mart turns into a finding.
    Every step shows the real data.

    > **Note:** the analysis notebooks read *only* the published marts. This one
    > deliberately breaks that rule — to explain the layers, it queries the raw
    > files and staging views directly (via `_lab.q(...)`).

    **The layers** (each numbered `transform/NN_*.sql` file is one view;
    `make transform` builds them in order and fails on any assertion):

    ```
    raw exports (S3)      →   staging (stg_*)        →   marts (mart_*)      →   analysis
    BBref / PBPStats /        parse, type, clean,        join, engineer,        regressions,
    DARKO / CleanTheGlass     one file per table         one row per unit       clustering, sims
    ```
    """)
    return


@app.cell
def _(mo):
    mo.md("""
    ## Explore any table
    Pick a staging or mart view to see its size, schema, and first rows.
    """)
    return


@app.cell
def _(mo, tables):
    tbl = mo.ui.dropdown(tables(), value="mart_lineup_features_league", label="table")
    tbl
    return (tbl,)


@app.cell
def _(mo, q, tbl):
    n = int(q(f"select count(*) c from {tbl.value}")["c"][0])
    schema = q(f"describe select * from {tbl.value}")[["column_name", "column_type"]]
    mo.vstack(
        [
            mo.md(f"**`{tbl.value}`** — {n:,} rows, {len(schema)} columns"),
            mo.ui.table(schema, selection=None, page_size=8),
            mo.md("first rows:"),
            mo.ui.table(q(f"select * from {tbl.value} limit 6"), selection=None),
        ]
    )
    return


@app.cell
def _(mo):
    mo.md("""
    ---
    ## 1 · The four raw sources

    Each answers a different question. They arrive as CSVs exported by hand
    (idempotent `make ingest` uploads them to `s3://nba-fit-lab/raw/…`).
    """)
    return


@app.cell
def _(RAW, mo, q):
    bb = q(f"""select "Team","Lineup","MP","PTS","eFG%"
              from read_csv_auto('{RAW}/bbref/2026-07-08/league_lineups_5man.csv')
              where "Team"='ORL' order by "MP" desc limit 3""")
    dk = q(
        "select player_name, team, dpm, o_dpm, d_dpm, mpg from stg_darko where team='Orlando Magic' order by mpg desc limit 4"
    )
    adv = q(
        "select player_name, team_bbref, usg, ast_pct, blk_pct from stg_player_advanced where team_bbref='ORL' order by mp desc limit 4"
    )
    ctg = q(
        "select player_name, freq_three, min from stg_ctg_player_league order by min desc limit 4"
    )
    mo.vstack(
        [
            mo.md(
                "**BBref — five-man lineups.** The outcome. Note `PTS`/`eFG%` are *signed differentials* (a validated net-rating-per-100, not raw totals):"
            ),
            mo.ui.table(bb, selection=None),
            mo.md(
                "**DARKO — player impact (DPM).** The talent baseline: a per-100 plus-minus estimate, split into offense/defense. This is what makes 'fit beyond talent' measurable:"
            ),
            mo.ui.table(dk, selection=None),
            mo.md(
                "**BBref advanced — per-player rates.** Usage/AST (creation), BLK%/DRB% (rim protection). Leaguewide, public:"
            ),
            mo.ui.table(adv, selection=None),
            mo.md(
                "**Cleaning the Glass — shot profile.** Garbage-time-filtered shooting frequency/accuracy by zone. *Paid, licensed — kept private; only derived aggregates are ever shared:*"
            ),
            mo.ui.table(ctg, selection=None),
        ]
    )
    return


@app.cell
def _(mo):
    mo.md("""
    ---
    ## 2 · Staging — turning exports into clean tables

    Staging is *faithful cleanup*: parse, type, and validate, one `.sql` file
    per table, with assertions that fail the build on bad data. No opinions yet.

    Watch one row of the BBref lineup export become a typed staging row. The raw
    `Lineup` is a `" | "`-joined string and `MP` is `"mm:ss"`; staging splits the
    five players, builds a sorted key, converts minutes, and strips the `+` off
    the signed net rating.
    """)
    return


@app.cell
def _(RAW, mo, q):
    raw1 = q(f"""select "Lineup","MP","PTS" from read_csv_auto('{RAW}/bbref/2026-07-08/league_lineups_5man.csv')
                where "Team"='ORL' order by "MP" desc limit 1""")
    staged1 = q("""select player_1,player_2,player_3,player_4,player_5,
                   round(minutes,1) as minutes, net_pts_per100
                   from stg_lineups_league where team='ORL' order by minutes desc limit 1""")
    mo.vstack(
        [
            mo.md("**raw** (one string, one clock time, one signed number):"),
            mo.ui.table(raw1, selection=None),
            mo.md(
                "**→ staged** (five columns, real minutes, a numeric net rating — plus 3 assertions like `minutes > 0` and `600 rows, 30 teams`):"
            ),
            mo.ui.table(staged1, selection=None),
        ]
    )
    return


@app.cell
def _(mo):
    mo.md("""
    ---
    ## 3 · The identity problem — matching players across sources

    Nothing shares a key. A lineup names players `"F. Last"` (`P. Banchero`);
    DARKO, heights, and advanced use full names; CTG has its own spellings. To
    put a player's DPM and BLK% onto a lineup, we normalize both sides to one
    key: first-initial + last name, accent-folded, suffix-stripped
    (`Wendell Carter Jr.` → `w. carter`).

    It mostly works — **99.8% of lineup slots resolve**. But `"F. Last"` is
    genuinely ambiguous when a team has two:
    """)
    return


@app.cell
def _(mo, q):
    coll = q("""select team_bbref as team, player_name, mp from stg_player_advanced
               where (team_bbref='OKC' and player_name like '%Williams')
                  or (team_bbref='GSW' and player_name like '%Curry')
               order by team_bbref, mp desc""")
    mo.vstack(
        [
            mo.md(
                "Both OKC Williamses collapse to `j. williams`; both Currys to `s. curry`:"
            ),
            mo.ui.table(coll, selection=None),
            mo.md(
                "The fix (in `mart_lineup_features_league`): on a key collision, attach the **higher-minutes** player (the star is meant nearly always), and give each source lineup its own id so distinct lineups aren't merged. A handful of bench-twin lineups get mis-attributed — a bounded, documented error."
            ),
        ]
    )
    return


@app.cell
def _(mo):
    mo.md("""
    ---
    ## 4 · Marts — the analysis contract

    Marts join staging into one row per unit of analysis, and add engineered
    columns (opinions). The workhorse is **`mart_lineup_features_league`**: one
    row per BBref 5-man lineup (600, all teams), with the outcome, a talent
    baseline, and continuous fit features.

    The key engineered idea — **fit = performance beyond talent**:

    > `fit_residual  =  net_pts_per100  −  talent_sum_dpm`

    where `talent_sum_dpm` = 5 × the lineup's minutes-weighted mean DPM. A
    positive residual means the lineup outplayed what its five players' individual
    value predicts.
    """)
    return


@app.cell
def _(mo, q):
    lf = q("""select team, round(minutes) as min, net_pts_per100 as net,
              round(talent_sum_dpm,1) as talent, round(fit_residual,1) as residual,
              round(rim_max_blk,1) as rim_blk, round(spacing_gravity_mean,1) as spacing
              from mart_lineup_features_league where team in ('ORL','NOP')
              order by minutes desc limit 8""")
    mo.vstack(
        [
            mo.md(
                "Orlando & New Orleans' most-used lineups — `net = talent + residual`:"
            ),
            mo.ui.table(lf, selection=None),
            mo.md(
                "`talent` is what DPM predicts; `residual` is the part fit *might* explain; `rim_blk` and `spacing` are the candidate explanations we test next."
            ),
        ]
    )
    return


@app.cell
def _(mo):
    mo.md("""
    ### Field by field — `mart_lineup_features_league`

    | field | what it is | how to read it | where it's silent |
    |---|---|---|---|
    | `net_pts_per100` | the **outcome**: points the lineup outscored opponents by per 100 possessions, on court | +5 good, −5 bad; ±10 is extreme | opponent-*averaged*, not adjusted; not garbage-time filtered |
    | `talent_sum_dpm` | **talent baseline**: sum of the five players' DARKO DPM (each player's standalone per-100 impact) | the net rating the *sum of the parts* predicts | assumes talent is additive — ignores diminishing returns |
    | `fit_residual` | `net − talent`: how far the group beat or missed its talent | +6 = played 6 better than the parts suggest | = real fit **+** DPM's own error **+** small-sample noise |
    | `minutes` | on-court time; also the regression **weight** | bigger row = more trustworthy | each team's ~top-20 lineups only |
    | `n_covered` | how many of the 5 slots matched a rostered player (0–5) | we analyze only `n_covered = 5` | ~9 deep-bench players league-wide have no profile |
    | `rim_max_blk` | **rim protection**: highest block rate (BLK%) among the five | a rim-protecting big pushes it up | BLK% is a proxy — misses verticality/positioning/deterrence-without-blocks |
    | `spacing_gravity_mean` | **spacing**: mean of players' 3PA-frequency × 3P-accuracy (willingness × ability) | how much the floor is stretched | doesn't capture off-ball movement / gravity |
    | `usg_spread`, `usg_max` | **shot-creation**: spread of usage rates, and the top usage | high = one dominant creator | usage ≠ creation *quality* |
    | `ast_max` | **playmaking**: the lineup's best assist rate | a primary passer raises it | AST% misses hockey assists / gravity passes |
    | `tallest_in` | **size**: tallest player, in inches | 84 = 7'0" | one player, not the lineup's overall size |

    **The gaps in one place:** the outcome is opponent-*averaged* (A3 will show that's mild — opponent style barely moves margin), it's each team's ~top-20 lineups over *one* season, and every fit feature is a *proxy* built from box-score-ish rates. Good enough to rank lineups; not to settle an argument. That honesty is why the analysis leans on intervals, not point estimates.
    """)
    return


@app.cell
def _(mo):
    mo.md("""
    ---
    ## 5 · A2 — how much is fit worth, on top of talent?

    **Step 1 — is the talent baseline any good?** Correlate `talent_sum_dpm`
    with actual `net_pts_per100` across the 595 fully-covered lineups.
    """)
    return


@app.cell
def _(load_mart, mo, np):
    d = load_mart("mart_lineup_features_league")
    d = d[d["n_covered"] == 5].dropna(subset=["spacing_gravity_mean"]).copy()
    r_corr = np.corrcoef(d["talent_sum_dpm"], d["net_pts_per100"])[0, 1]
    mo.md(
        f"""
        Correlation of talent with net rating: **r = {r_corr:.2f}** (across {len(d)} lineups).
        Strong and positive — talent alone carries most of the signal. Everything
        below asks whether the *leftover* has structure.
        """
    )
    return (d,)


@app.cell
def _(mo):
    mo.md("""
    **Step 2 — the regression.** Minutes-weighted least squares of net rating on
    talent + four continuous fit features, standardized so the coefficients are
    comparable (per +1 SD), with standard errors **clustered by team** (600
    lineups come from only 30 teams — they aren't independent).
    """)
    return


@app.cell
def _(d, mo, pd, sm):
    feats = [
        "talent_sum_dpm",
        "rim_max_blk",
        "spacing_gravity_mean",
        "usg_spread",
        "ast_max",
    ]
    nice = {
        "talent_sum_dpm": "talent (ΣDPM)",
        "rim_max_blk": "rim protection",
        "spacing_gravity_mean": "spacing (gravity)",
        "usg_spread": "usage balance",
        "ast_max": "playmaking",
    }
    Z = (d[feats] - d[feats].mean()) / d[feats].std()
    m = sm.WLS(d["net_pts_per100"], sm.add_constant(Z), weights=d["minutes"]).fit(
        cov_type="cluster", cov_kwds={"groups": d["team"].astype("category").cat.codes}
    )
    ci = m.conf_int()
    a2_tab = pd.DataFrame(
        {
            "feature": [nice[f] for f in feats],
            "coef (per SD)": [round(m.params[f], 2) for f in feats],
            "95% CI": [f"[{ci.loc[f, 0]:+.1f}, {ci.loc[f, 1]:+.1f}]" for f in feats],
            "p": [round(m.pvalues[f], 3) for f in feats],
            "clears 0?": ["✓ yes" if m.pvalues[f] < 0.05 else "no" for f in feats],
        }
    )
    r2t = (
        sm.WLS(
            d["net_pts_per100"],
            sm.add_constant(Z[["talent_sum_dpm"]]),
            weights=d["minutes"],
        )
        .fit()
        .rsquared
    )
    mo.vstack(
        [
            mo.ui.table(a2_tab, selection=None),
            mo.md(f"""
        **Read it:** talent dominates. Of the fit features, **only rim protection
        clears zero** — even spacing measured properly (gravity = willingness ×
        accuracy) sits on the line. Talent alone explains **{r2t:.0%}** of variance;
        all fit features together add only **{(m.rsquared - r2t):.0%}** more. That's the
        whole A2 finding: *fit is real but second-order, and the part that survives is
        rim protection, not the spacing the discourse fixates on.*
        """),
        ]
    )
    return


@app.cell
def _(mo):
    mo.md("""
    ### How to read that regression table

    - **coef (per SD)** — the features live on different scales (BLK% ~1–8, gravity ~5–20), so each is *standardized* to mean 0, SD 1 first. The coefficient then reads: *"points of net rating per **one standard deviation** more of this feature, holding the others fixed"* — directly comparable across rows. Rim protection's ≈ +1.4 means a typical bump in rim protection buys ~1.4 net/100.
    - **95% CI** — the plausible range for the coefficient. If it **includes 0**, we can't distinguish the effect from noise. Only rim protection's interval sits entirely above zero.
    - **p** — the chance of seeing an effect this big if the truth were zero; < 0.05 is the usual "real" bar.
    - **clustered by team** — 600 lineups but only 30 teams, and lineups from one team share its coaching, health, and system, so they aren't independent observations. Clustering widens the intervals *honestly* — naïve standard errors would overstate our certainty roughly 4×.
    - **R² (17% → 19%)** — the share of net-rating *variance* the model explains. Talent alone gets ~17%; adding every fit feature reaches ~19%. That **+2% is the ceiling** on how much fit can possibly matter here.

    **Where it's silent:** this describes *associations*, not causes — teams that build rim protection also tend to defend and coach well, and we can't fully peel those apart. And "spacing doesn't clear zero" means *undetectable at this sample*, not *proven to be zero*.
    """)
    return


@app.cell
def _(mo):
    mo.md("""
    ---
    ## 6 · A3 — does opponent style matter?

    **Step 1 — do teams even cluster into archetypes?** Standardize
    `mart_team_style` and run k-means for several k, scoring each by *silhouette*
    (separation) and *stability* (agreement across random seeds).
    """)
    return


@app.cell
def _(
    KMeans,
    StandardScaler,
    adjusted_rand_score,
    load_mart,
    mo,
    np,
    pd,
    silhouette_score,
):
    ts = load_mart("mart_team_style")
    sf = [
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
    X = StandardScaler().fit_transform(ts[sf])
    a3_rows = []
    for k in range(3, 8):
        sil = silhouette_score(X, KMeans(k, n_init=10, random_state=0).fit_predict(X))
        labs = [KMeans(k, n_init=10, random_state=s).fit_predict(X) for s in range(6)]
        ari = np.mean(
            [
                adjusted_rand_score(labs[i], labs[j])
                for i in range(6)
                for j in range(i + 1, 6)
            ]
        )
        a3_rows.append(
            {"k": k, "silhouette": round(sil, 3), "seed stability (ARI)": round(ari, 2)}
        )
    mo.vstack(
        [
            mo.ui.table(pd.DataFrame(a3_rows), selection=None),
            mo.md(
                "Silhouette never clears ~0.12 (≥0.25 is where clusters get trustworthy) and seeds disagree. **NBA styles are a continuum, not clean types** — so we skip fake buckets and ask the question directly."
            ),
        ]
    )
    return


@app.cell
def _(mo):
    mo.md("""
    ### What those two scores mean

    - **silhouette** — for each team, how much closer it sits to its *own* cluster than to the nearest *other* cluster, averaged over all teams. Runs −1 to +1: **> 0.5** strong, **0.25–0.5** reasonable, **< 0.25** the clusters overlap so much they're barely real. We top out at ~0.12.
    - **seed stability (ARI)** — k-means starts from random seeds; ARI measures how much two runs *agree* on who's grouped with whom (1 = identical, 0 = coin-flip). Ours ~0.4 means re-running literally reshuffles teams between "archetypes."

    Together they say the archetypes are a **story we impose**, not structure in the data — team style is a smooth spectrum (a little faster, a little more rim-heavy). So rather than force 30 teams into 5 boxes, A3 keeps opponent style as **continuous numbers** and asks what they actually move. This is the same instinct as A2 dropping binary "shooter" flags for continuous gravity: *don't bucket a spectrum.*
    """)
    return


@app.cell
def _(mo):
    mo.md("""
    **Step 2 — process vs outcome.** Regress our per-game numbers on the
    opponent's *quality* (their season net rating) plus their *style*. Style
    moves how we play; it doesn't move the result.
    """)
    return


@app.cell
def _(load_mart, mo, pd, sm):
    g = load_mart("mart_games_styled")
    g["home"] = (~g["is_away"]).astype(int)

    def f(y, xs):
        return sm.OLS(g[y], sm.add_constant(g[xs])).fit(cov_type="HC1")

    mix = f(
        "three_pa_rate", ["opp_def_three_pa_rate_allowed", "opp_def_pts_poss", "home"]
    )
    pace = f("pace", ["opp_pace", "home"])
    style = [
        "opp_off_rim_rate",
        "opp_off_three_pa_rate",
        "opp_def_tov_forced_pct",
        "opp_def_rim_rate_allowed",
    ]
    mrg = f("margin", ["opp_net_pts_poss", "home"] + style)
    a3_tab = pd.DataFrame(
        {
            "we regress…": [
                "our 3PA rate",
                "our pace",
                "our margin",
                "our margin",
                "our margin",
            ],
            "…on": [
                "opponent allows 3s (style)",
                "opponent pace (style)",
                "opponent quality",
                "home court",
                "any opponent style",
            ],
            "coef": [
                round(mix.params["opp_def_three_pa_rate_allowed"], 3),
                round(pace.params["opp_pace"], 2),
                round(mrg.params["opp_net_pts_poss"], 2),
                round(mrg.params["home"], 2),
                "—",
            ],
            "p": [
                round(mix.pvalues["opp_def_three_pa_rate_allowed"], 3),
                round(pace.pvalues["opp_pace"], 3),
                round(mrg.pvalues["opp_net_pts_poss"], 3),
                round(mrg.pvalues["home"], 3),
                round(min(mrg.pvalues[c] for c in style), 3),
            ],
            "verdict": [
                "PROCESS ✓",
                "PROCESS ✓",
                "OUTCOME ✓",
                "OUTCOME ✓",
                "OUTCOME ✗ (n.s.)",
            ],
        }
    )
    mo.vstack(
        [
            mo.ui.table(a3_tab, selection=None),
            mo.md(
                "Opponent style bends our shot mix and tempo (p<0.001) but does nothing to margin — the scoreboard is opponent quality + home court. **Style shapes how you play, not whether you win.**"
            ),
        ]
    )
    return


@app.cell
def _(mo):
    mo.md("""
    ### Why "process vs outcome" is the whole point

    Each row regresses one of *our* per-game numbers on the opponent's traits, HC-robust
    (standard errors that tolerate games being unequally noisy). The tell is that the
    **3rd and 5th rows use the same opponent trait** — "opponent allows threes":

    - it → **our 3PA rate rises** (a *process* we can measure, p < 0.001)
    - it → **our margin doesn't budge** (the *outcome*, not significant)

    So opponent style is real and legible — it visibly bends how we play — but it
    **doesn't reach the scoreboard** once you know how *good* the opponent is
    (`opp_net_pts_poss`, their season net rating) and where the game is played
    (`home`, worth ~+4 points). *Style is preparation, not prediction.*

    **Where it's silent:** margin is opponent-averaged at the *team* level and we can't
    see individual *matchups* (who guarded whom). A genuine scheme edge in a seven-game
    series could hide under an 82-game average — this rules out a big, blunt, season-long
    style effect, not every situational one.
    """)
    return


@app.cell
def _(mo):
    mo.md("""
    ---
    ## 7 · A4 — from a roster to a distribution of wins

    **The engine, in one line:** team net rating = `5 × minutes-weighted mean
    player DPM`; then Pythagorean wins from that net rating. The full roster is
    required — the deep bench is exactly what drags a bad team. Check calibration
    against what actually happened:
    """)
    return


@app.cell
def _(load_mart, mo, pd, q):
    rost = load_mart("mart_roster")

    def pyth(net, exp=13.91, ppg=115.0):
        pf, pa = ppg + net / 2, ppg - net / 2
        return 82 * pf**exp / (pf**exp + pa**exp)

    actual = q("""select regexp_replace(column01,'\\*$','') as team_name, cast(column03 as int) as w
                 from read_csv('s3://nba-fit-lab/raw/bbref/2026-07-08/league_team_advanced.csv',
                 header=false, skip=6, all_varchar=true) where column01 not in ('','League Average')""")
    a4_rows = []
    for tm, name in [
        ("ORL", "Orlando Magic"),
        ("NOP", "New Orleans Pelicans"),
        ("OKC", "Oklahoma City Thunder"),
        ("WAS", "Washington Wizards"),
    ]:
        r_cal = rost[rost["team"] == tm]
        net_cal = 5 * (r_cal["dpm"] * r_cal["mpg"]).sum() / r_cal["mpg"].sum()
        aw = int(actual[actual["team_name"] == name]["w"].iloc[0])
        a4_rows.append(
            {
                "team": tm,
                "proj net": round(net_cal, 1),
                "proj wins": round(pyth(net_cal)),
                "actual wins": aw,
                "error": round(pyth(net_cal)) - aw,
            }
        )
    mo.vstack(
        [
            mo.ui.table(pd.DataFrame(a4_rows), selection=None),
            mo.md(
                "Within a couple of wins across good and bad teams — the DPM → Pythagorean chain is sound."
            ),
        ]
    )
    return


@app.cell
def _(mo):
    mo.md("""
    ### How the projection works, field by field

    - **proj net** = `5 × (minutes-weighted mean DPM)`. Five players are on the floor at
      once, so a team's expected net rating is 5× the average DPM of whoever's playing,
      weighted by minutes. Exactly A2's "sum of the parts," applied to the whole roster
      instead of one lineup — and it needs the *full* roster, because a bad team's drag
      is its deep bench, which a top-10 view would hide.
    - **proj wins** = **Pythagorean expectation**. Turn net rating into points-for and
      points-against (≈ 115 ± net/2 per game), then
      `wins = 82 × PF^13.91 / (PF^13.91 + PA^13.91)`. The exponent 13.91 is the
      empirically-fit "how strongly does outscoring convert to winning" constant for the
      NBA — steep, because basketball has little luck over 82 games.
    - **actual wins / error** — the reality check. Errors of a game or two across good
      (OKC) and bad (WAS) teams say the chain holds: **individual talent + minutes → team
      wins**, no fit term required to land close. (Which is A2 again: fit is a small
      correction on a talent-dominated forecast.)

    **Where it's silent:** these are *last* season's rosters and minutes. A real forecast
    needs *next* season's minutes — injuries, trades, a young player's leap — which are
    genuinely uncertain. That's the point of the simulation below: it turns that
    uncertainty into a **range of wins** instead of a false-precision single number.
    """)
    return


@app.cell
def _(load_mart, mo, np):
    rr = load_mart("mart_roster")
    r_sim = rr[rr["team"] == "ORL"]
    dpm, w = r_sim["dpm"].to_numpy(float), r_sim["mpg"].to_numpy(float)
    rng = np.random.default_rng(0)
    dpm_d = dpm + rng.normal(0, 1.2, (4000, len(dpm)))
    min_d = w * np.exp(rng.normal(0, 0.15, (4000, len(w))))
    net_sim = 5 * (dpm_d * min_d).sum(1) / min_d.sum(1)

    def pw(n):
        pf, pa = 115 + n / 2, 115 - n / 2
        return 82 * pf**13.91 / (pf**13.91 + pa**13.91)

    wins = pw(net_sim)
    p5, p50, p95 = np.percentile(wins, [5, 50, 95])
    mo.md(
        f"""
        **Why a distribution, not a number.** DPM and minutes are uncertain
        (injuries, role changes, model error). Simulate the season 4,000 times
        drawing each — Orlando lands at a **median {p50:.0f} wins, 90% range
        {p5:.0f}–{p95:.0f}**. A point estimate would hide a ±7-win reality. The A4
        notebook makes this interactive and prices roster moves in wins.
        """
    )
    return


@app.cell
def _(mo):
    mo.md("""
    ---
    ## 8 · The conclusion, assembled

    Every layer points one way:

    | analysis | question | answer |
    |---|---|---|
    | **A2** | what is lineup fit worth? | talent explains ~17%; fit adds ~2%, and only **rim protection** clears zero — spacing (even as gravity) doesn't |
    | **A3** | does opponent style matter? | it moves your **process** (shot mix, pace) but not your **margin** — quality + home court decide games |
    | **A4** | what does a roster project to? | a **distribution** of wins; a realistic talent move dwarfs any fit tweak |

    **The thesis:** measured honestly on one season, basketball outcomes are
    dominated by talent and quality. The stylistic effects the discourse obsesses
    over are real but *second-order* — small (rim protection) or *process-only*
    (shot mix, pace). Fit is worth pricing; it is not worth mistaking for talent.

    Everything above is reproducible: export CSVs → `make ingest transform` →
    open a notebook. Data via BBref, PBPStats, DARKO, and Cleaning the Glass.
    """)
    return


@app.cell
def _():
    import marimo as mo
    import numpy as np
    import pandas as pd
    import statsmodels.api as sm
    from sklearn.cluster import KMeans
    from sklearn.metrics import adjusted_rand_score, silhouette_score
    from sklearn.preprocessing import StandardScaler

    from _lab import RAW, load_mart, q, tables

    return (
        KMeans,
        RAW,
        StandardScaler,
        adjusted_rand_score,
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
