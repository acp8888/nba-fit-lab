-- transform/32_mart_star_supporting_cast.sql
-- Mart: the REALIZED supporting-cast fingerprint per (season, team, star), aggregated from
-- mart_star_teammate_context. Answers "what environment did the star actually play in?" with
-- co-minute-weighted teammate traits (weighting by shared minutes, so who the star played
-- WITH — not who was merely on the roster — drives every number). Continuous measures are the
-- robust ones; the "n teammates >=25% exposure who are shooters/creators/rim-protectors" counts
-- are coarser (binary flags) and should be read as directional.
--
-- This is the continuous replacement the brief (§9, §7) asks for: instead of a binary
-- duplicate/complement label, describe the star's realized spacing/talent/rim environment on a
-- scale. Finding from the prototype: Paolo's and Zion's 2025-26 co-minute spacing environments
-- are nearly identical (cast C&S pctl ~50 vs ~49) — the clean "starved vs spaced" contrast does
-- not survive co-minute weighting. Availability differs far more (Zion's on-court minutes run
-- well below Paolo's), which is why availability, not spacing, anchors the ORL-vs-NOP story.

with c as (select * from mart_star_teammate_context)

select
  team,
  star,
  max(star_oncourt_min)                                                                         as star_oncourt_min,
  -- co-minute-weighted teammate traits (the realized environment)
  round(sum(shared_min * tm_dpm) filter (where tm_dpm is not null)
        / nullif(sum(shared_min) filter (where tm_dpm is not null), 0), 2)                      as cast_dpm,
  round(sum(shared_min * tm_csg_pctl) filter (where tm_csg_pctl is not null)
        / nullif(sum(shared_min) filter (where tm_csg_pctl is not null), 0))                    as cast_csg_pctl,
  round(sum(shared_min * tm_rim_freq_pctl) filter (where tm_rim_freq_pctl is not null)
        / nullif(sum(shared_min) filter (where tm_rim_freq_pctl is not null), 0))               as cast_rimf_pctl,
  round(sum(shared_min * tm_height_in) filter (where tm_height_in is not null)
        / nullif(sum(shared_min) filter (where tm_height_in is not null), 0), 1)                as cast_height_in,
  -- coarse "surrounded by" counts: distinct teammates the star shared >=25% of its minutes with
  count(distinct teammate) filter (where tm_is_shooter and pct_star_min_shared >= 25)           as n_shooters_hi,
  count(distinct teammate) filter (where tm_is_creator and pct_star_min_shared >= 25)           as n_creators_hi,
  count(distinct teammate) filter (where tm_is_rim_protector and pct_star_min_shared >= 25)      as n_rimprot_hi,
  count(distinct teammate) filter (where pct_star_min_shared >= 25)                             as n_teammates_hi,
  season
from c
group by season, team, star

-- ASSERTIONS (enforced by run.py):
-- ASSERT == 4: SELECT count(*) FROM mart_star_supporting_cast
-- ASSERT == 2: SELECT count(DISTINCT season) FROM mart_star_supporting_cast
-- co-minute-weighted percentiles land in [0,100]
-- ASSERT == 0: SELECT count(*) FROM mart_star_supporting_cast WHERE cast_csg_pctl NOT BETWEEN 0 AND 100
-- every star-season has a resolved talent environment
-- ASSERT == 0: SELECT count(*) FROM mart_star_supporting_cast WHERE cast_dpm IS NULL
-- realized 2025-26 spacing environments are close (the demoted duplicate/complement contrast):
-- ASSERT <= 12: SELECT round(abs(max(cast_csg_pctl) filter (where team='ORL') - max(cast_csg_pctl) filter (where team='NOP'))) FROM mart_star_supporting_cast WHERE season = 2026
